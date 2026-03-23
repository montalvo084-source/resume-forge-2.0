import io
import os

from dotenv import load_dotenv
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   send_file, session, url_for)

load_dotenv()

from models import Application, MasterResume, Setting, db, seed_settings


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resumeforge.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit

    db.init_app(app)

    with app.app_context():
        os.makedirs(app.instance_path, exist_ok=True)
        db.create_all()
        seed_settings()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _get_total():
        starting = int(Setting.get('starting_count', 0))
        return starting + Application.query.count()

    def _next_milestone(total):
        for m in [5, 10, 25, 50, 75, 100]:
            if total < m:
                return m
        return None

    def _run_resume_review(content: str):
        """Run AI review and store result in session. Silently skips on API error."""
        from ai import review_master_resume
        try:
            result = review_master_resume(content)
            if result['has_changes']:
                session['resume_review'] = {
                    'corrected': result['corrected'],
                    'changes': result['changes'],
                }
            else:
                session.pop('resume_review', None)
        except Exception:
            session.pop('resume_review', None)

    # ------------------------------------------------------------------ #
    # Dashboard
    # ------------------------------------------------------------------ #

    @app.route('/')
    def dashboard():
        total = _get_total()
        goal = int(Setting.get('goal_total', 100))
        progress = min(100, round(total / goal * 100)) if goal else 0
        recent = Application.query.order_by(Application.applied_at.desc()).limit(5).all()
        show_onboarding = (
            Setting.get('starting_count', '0') == '0'
            and Application.query.count() == 0
        )
        return render_template(
            'dashboard.html',
            total=total,
            goal=goal,
            progress=progress,
            recent=recent,
            next_milestone=_next_milestone(total),
            user_name=Setting.get('user_name', 'Gabriel'),
            goal_quarter=Setting.get('goal_quarter', 'Q2 2025'),
            show_onboarding=show_onboarding,
        )

    # ------------------------------------------------------------------ #
    # Master Resume
    # ------------------------------------------------------------------ #

    @app.route('/resume', methods=['GET'])
    def resume():
        r = MasterResume.get()
        review = session.pop('resume_review', None)
        return render_template('resume.html', resume=r, review=review)

    @app.route('/resume/save', methods=['POST'])
    def resume_save():
        content = request.form.get('content', '').strip()
        if not content:
            flash('Resume content cannot be empty.', 'error')
            return redirect(url_for('resume'))
        MasterResume.upsert(content)
        flash('Resume saved. Reviewing for errors...', 'success')
        _run_resume_review(content)
        return redirect(url_for('resume'))

    @app.route('/resume/upload', methods=['POST'])
    def resume_upload():
        f = request.files.get('resume_file')
        if not f or f.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('resume'))

        filename = f.filename.lower()
        try:
            if filename.endswith('.txt'):
                content = f.read().decode('utf-8', errors='replace')
            elif filename.endswith('.pdf'):
                content = _extract_pdf(f)
            elif filename.endswith('.docx'):
                content = _extract_docx(f)
            else:
                flash('Unsupported file type. Please upload a PDF, DOCX, or TXT file.', 'error')
                return redirect(url_for('resume'))
        except Exception as e:
            flash(f'Could not extract text from file: {e}', 'error')
            return redirect(url_for('resume'))

        if not content.strip():
            flash('Could not extract any text from the file.', 'error')
            return redirect(url_for('resume'))

        content = content.strip()
        MasterResume.upsert(content)
        flash('Resume uploaded. Reviewing for errors...', 'success')
        _run_resume_review(content)
        return redirect(url_for('resume'))

    @app.route('/resume/accept-review', methods=['POST'])
    def resume_accept_review():
        review = session.pop('resume_review', None)
        if review and review.get('corrected'):
            MasterResume.upsert(review['corrected'])
            flash('Corrections applied and saved.', 'success')
        else:
            flash('No pending review to accept.', 'error')
        return redirect(url_for('resume'))

    @app.route('/resume/dismiss-review', methods=['POST'])
    def resume_dismiss_review():
        session.pop('resume_review', None)
        flash('Original kept — no changes made.', 'success')
        return redirect(url_for('resume'))

    def _extract_pdf(f):
        try:
            import pdfplumber
            with pdfplumber.open(f) as pdf:
                return '\n'.join(
                    page.extract_text() or '' for page in pdf.pages
                )
        except ImportError:
            pass
        import fitz  # PyMuPDF
        data = f.read()
        doc = fitz.open(stream=data, filetype='pdf')
        return '\n'.join(page.get_text() for page in doc)

    def _extract_docx(f):
        from docx import Document
        doc = Document(f)
        return '\n'.join(p.text for p in doc.paragraphs)

    # ------------------------------------------------------------------ #
    # Apply flow
    # ------------------------------------------------------------------ #

    @app.route('/apply', methods=['GET'])
    def apply():
        return render_template('apply.html')

    @app.route('/apply/generate', methods=['POST'])
    def apply_generate():
        company = request.form.get('company', '').strip()
        job_title = request.form.get('job_title', '').strip()
        job_description = request.form.get('job_description', '').strip()
        why_applying = request.form.get('why_applying', '').strip()

        if not company or not job_title or not job_description:
            flash('Company, job title, and job description are required.', 'error')
            return redirect(url_for('apply'))

        master = MasterResume.get()
        if not master or not master.content.strip():
            flash('Please add your master resume before generating.', 'error')
            return redirect(url_for('resume'))

        from ai import normalize_application_inputs, tailor_resume
        from resume_parser import parse_resume
        from resume_renderer import render_html

        # Normalize company name and job title
        corrected_company = False
        corrected_title = False
        try:
            normalized = normalize_application_inputs(company, job_title)
            company = normalized['company']
            job_title = normalized['job_title']
            corrected_company = normalized['corrected_company']
            corrected_title = normalized['corrected_title']
        except Exception:
            pass  # Silently fall back to original if normalization fails

        try:
            raw_text = tailor_resume(
                master_resume=master.content,
                job_title=job_title,
                company=company,
                job_description=job_description,
                why_applying=why_applying,
            )
        except Exception as e:
            flash(f'AI generation failed: {e}', 'error')
            return redirect(url_for('apply'))

        parsed = parse_resume(raw_text)
        user_name = Setting.get('user_name', 'Gabriel')
        html_content = render_html(parsed, user_name)

        new_app = Application(
            company=company,
            job_title=job_title,
            job_description=job_description,
            why_applying=why_applying,
            tailored_resume_text=raw_text,
            tailored_resume_html=html_content,
            status='applied',
            corrected_company=corrected_company,
            corrected_title=corrected_title,
        )
        db.session.add(new_app)
        db.session.commit()

        return redirect(url_for('apply_result', id=new_app.id, new='1'))

    @app.route('/apply/result/<int:id>', methods=['GET'])
    def apply_result(id):
        application = db.session.get(Application, id)
        if application is None:
            flash('Application not found.', 'error')
            return redirect(url_for('dashboard'))
        fire_confetti = request.args.get('new') == '1'
        total = _get_total()
        return render_template(
            'result.html',
            application=application,
            fire_confetti=fire_confetti,
            total=total,
        )

    @app.route('/apply/result/<int:id>/regenerate', methods=['POST'])
    def apply_regenerate(id):
        old_app = db.session.get(Application, id)
        if old_app is None:
            flash('Application not found.', 'error')
            return redirect(url_for('dashboard'))

        master = MasterResume.get()
        if not master:
            flash('No master resume found.', 'error')
            return redirect(url_for('resume'))

        from ai import tailor_resume
        from resume_parser import parse_resume
        from resume_renderer import render_html

        try:
            raw_text = tailor_resume(
                master_resume=master.content,
                job_title=old_app.job_title,
                company=old_app.company,
                job_description=old_app.job_description or '',
                why_applying=old_app.why_applying or '',
            )
        except Exception as e:
            flash(f'Regeneration failed: {e}', 'error')
            return redirect(url_for('apply_result', id=id))

        parsed = parse_resume(raw_text)
        user_name = Setting.get('user_name', 'Gabriel')
        html_content = render_html(parsed, user_name)

        old_app.tailored_resume_text = raw_text
        old_app.tailored_resume_html = html_content
        db.session.commit()

        flash('Resume regenerated.', 'success')
        return redirect(url_for('apply_result', id=id))

    # ------------------------------------------------------------------ #
    # Downloads
    # ------------------------------------------------------------------ #

    @app.route('/apply/result/<int:id>/download/pdf')
    def download_pdf(id):
        from resume_renderer import render_pdf
        row = db.session.get(Application, id)
        if row is None or not row.tailored_resume_html:
            flash('Resume not found.', 'error')
            return redirect(url_for('dashboard'))
        try:
            pdf_bytes = render_pdf(row.tailored_resume_html)
        except Exception as e:
            flash(f'PDF generation failed: {e}. Make sure WeasyPrint is installed.', 'error')
            return redirect(url_for('apply_result', id=id))
        filename = f"{row.company}_{row.job_title}_resume.pdf".replace(' ', '_')
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename,
        )

    @app.route('/apply/result/<int:id>/download/docx')
    def download_docx(id):
        from resume_parser import parse_resume
        from resume_renderer import render_docx
        row = db.session.get(Application, id)
        if row is None or not row.tailored_resume_text:
            flash('Resume not found.', 'error')
            return redirect(url_for('dashboard'))
        parsed = parse_resume(row.tailored_resume_text)
        user_name = Setting.get('user_name', 'Gabriel')
        docx_bytes = render_docx(parsed, user_name)
        filename = f"{row.company}_{row.job_title}_resume.docx".replace(' ', '_')
        return send_file(
            io.BytesIO(docx_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=filename,
        )

    # ------------------------------------------------------------------ #
    # Applications history
    # ------------------------------------------------------------------ #

    @app.route('/applications', methods=['GET'])
    def applications():
        status_filter = request.args.get('status', 'all')
        search_query = request.args.get('q', '').strip()
        total = _get_total()

        query = Application.query.order_by(Application.applied_at.desc())
        if status_filter != 'all':
            query = query.filter(Application.status == status_filter)
        if search_query:
            like = f'%{search_query}%'
            query = query.filter(
                db.or_(
                    Application.company.ilike(like),
                    Application.job_title.ilike(like),
                )
            )

        return render_template(
            'applications.html',
            applications=query.all(),
            total=total,
            current_status=status_filter,
            search_query=search_query,
        )

    @app.route('/applications/<int:id>/update', methods=['POST'])
    def update_application(id):
        row = db.session.get(Application, id)
        if row is None:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        data = request.get_json() or {}
        if 'status' in data:
            row.status = data['status']
        if 'notes' in data:
            row.notes = data['notes']
        db.session.commit()
        return jsonify({'success': True})

    # ------------------------------------------------------------------ #
    # Settings
    # ------------------------------------------------------------------ #

    @app.route('/settings', methods=['GET', 'POST'])
    def settings_page():
        if request.method == 'POST':
            Setting.set('user_name', request.form.get('user_name', 'Gabriel').strip())
            Setting.set('goal_total', request.form.get('goal_total', '100').strip())
            Setting.set('goal_quarter', request.form.get('goal_quarter', 'Q2 2025').strip())
            Setting.set('starting_count', request.form.get('starting_count', '0').strip())
            flash('Settings saved.', 'success')
            return redirect(url_for('settings_page'))

        settings = {
            'user_name': Setting.get('user_name', 'Gabriel'),
            'goal_total': Setting.get('goal_total', '100'),
            'goal_quarter': Setting.get('goal_quarter', 'Q2 2025'),
            'starting_count': Setting.get('starting_count', '0'),
        }
        return render_template('settings.html', settings=settings)

    @app.route('/settings/starting-count', methods=['POST'])
    def set_starting_count():
        count = request.form.get('starting_count', '0').strip()
        try:
            count = str(max(0, int(count)))
        except ValueError:
            count = '0'
        Setting.set('starting_count', count)
        return redirect(url_for('dashboard'))

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
