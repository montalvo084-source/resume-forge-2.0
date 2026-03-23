import re

SECTION_HEADERS = ['CONTACT', 'SUMMARY', 'EXPERIENCE', 'SKILLS', 'EDUCATION']

_HEADER_RE = re.compile(
    r'^(' + '|'.join(SECTION_HEADERS) + r')\s*:?\s*$',
    re.MULTILINE | re.IGNORECASE
)


def parse_resume(text: str) -> dict:
    sections = _split_sections(text)
    return {
        'contact': _parse_contact(sections.get('CONTACT', '')),
        'summary': sections.get('SUMMARY', '').strip(),
        'experience': _parse_experience(sections.get('EXPERIENCE', '')),
        'skills': _parse_skills(sections.get('SKILLS', '')),
        'education': _parse_education(sections.get('EDUCATION', '')),
    }


def _split_sections(text: str) -> dict:
    sections = {}
    matches = list(_HEADER_RE.finditer(text))
    for i, match in enumerate(matches):
        header = match.group(1).upper()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[header] = text[start:end].strip()
    return sections


def _parse_contact(text: str) -> dict:
    contact = {}
    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        # Handle pipe-separated contact fields on one line:
        # "Email: foo@bar.com | Phone: 555 | LinkedIn: ..."
        if '|' in raw_line and ':' in raw_line:
            segments = [s.strip() for s in raw_line.split('|')]
            for seg in segments:
                if ':' in seg:
                    key, _, value = seg.partition(':')
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    if key and value:
                        contact[key] = value
            continue

        if ':' in raw_line:
            key, _, value = raw_line.partition(':')
            key = key.strip().lower().replace(' ', '_')
            value = value.strip()
            if key and value:
                contact[key] = value
        elif not contact:
            # First non-colon, non-pipe line is the name
            contact['name'] = raw_line

    return contact


def _parse_experience(text: str) -> list:
    """
    Expected AI format (most common):
      Company Name | Location | Start – End
      Job Title
      - Bullet one
      - Bullet two

    We collect consecutive non-bullet lines as the "header block" for a job,
    then assign bullets to the most recent job once bullets appear.
    A new non-bullet line after bullets starts a new job.
    """
    jobs = []
    current_job = None
    pending_header_lines = []  # non-bullet lines before we've seen any bullets

    def _flush_header(job, lines):
        if not lines:
            return
        # Find a pipe-separated line first (company | location | dates)
        pipe_line_idx = next((i for i, l in enumerate(lines) if '|' in l), None)
        if pipe_line_idx is not None:
            parts = [p.strip() for p in lines[pipe_line_idx].split('|')]
            job['company'] = parts[0] if len(parts) > 0 else ''
            job['dates'] = parts[-1] if len(parts) > 1 else ''
            # All non-pipe lines (before or after) are the role title
            title_lines = [l for i, l in enumerate(lines) if i != pipe_line_idx]
            job['title'] = ' '.join(title_lines).strip() or parts[0]
        elif len(lines) >= 2:
            # First line = company, second = title
            job['company'] = lines[0]
            job['title'] = lines[1]
            job['dates'] = lines[2] if len(lines) > 2 else ''
        else:
            job['title'] = lines[0] if lines else ''

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        is_bullet = stripped[0] in ('-', '•', '*', '–')

        if not is_bullet:
            if current_job is not None and current_job.get('bullets'):
                # Non-bullet after bullets → new job
                _flush_header(current_job, pending_header_lines)
                pending_header_lines = []
                current_job = {'title': '', 'company': '', 'dates': '', 'bullets': []}
                jobs.append(current_job)
                pending_header_lines.append(stripped)
            else:
                # Still collecting the header block for the current/new job
                if current_job is None:
                    current_job = {'title': '', 'company': '', 'dates': '', 'bullets': []}
                    jobs.append(current_job)
                pending_header_lines.append(stripped)
        else:
            if current_job is None:
                current_job = {'title': '', 'company': '', 'dates': '', 'bullets': []}
                jobs.append(current_job)
            if pending_header_lines:
                _flush_header(current_job, pending_header_lines)
                pending_header_lines = []
            bullet_text = re.sub(r'^[-•*–]\s*', '', stripped)
            current_job['bullets'].append(bullet_text)

    # Flush any remaining header
    if current_job is not None and pending_header_lines:
        _flush_header(current_job, pending_header_lines)

    return jobs


def _parse_skills(text: str) -> dict:
    skills = {}
    current_category = 'General'
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('-') or stripped.startswith('•'):
            item = re.sub(r'^[-•]\s*', '', stripped)
            skills.setdefault(current_category, []).append(item)
        elif ':' in stripped:
            cat, _, items_str = stripped.partition(':')
            current_category = cat.strip()
            items = [s.strip() for s in items_str.split(',') if s.strip()]
            if items:
                skills[current_category] = items
            else:
                skills.setdefault(current_category, [])
        else:
            skills.setdefault(current_category, []).append(stripped)
    return skills


def _parse_education(text: str) -> list:
    edu_list = []
    current = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                edu_list.append(current)
                current = {}
            continue
        stripped = re.sub(r'^[-•]\s*', '', stripped)
        if not current:
            # Try comma-separated single line: "Degree, School, Year"
            if ',' in stripped:
                parts = [p.strip() for p in stripped.split(',')]
                current['degree'] = parts[0]
                current['school'] = parts[1] if len(parts) > 1 else ''
                current['year'] = parts[2] if len(parts) > 2 else ''
                edu_list.append(current)
                current = {}
            # Try pipe-separated single line
            elif '|' in stripped:
                parts = [p.strip() for p in stripped.split('|')]
                current['degree'] = parts[0]
                current['school'] = parts[1] if len(parts) > 1 else ''
                current['year'] = parts[2] if len(parts) > 2 else ''
                edu_list.append(current)
                current = {}
            else:
                current['degree'] = stripped
        elif 'school' not in current:
            current['school'] = stripped
        else:
            current['year'] = stripped
    if current:
        edu_list.append(current)
    return edu_list
