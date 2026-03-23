import json
import os

import anthropic

client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

SYSTEM_PROMPT = """You are a professional resume writer. Your job is to take a person's master resume and tailor it to a specific job posting — highlighting the most relevant experience, skills, and accomplishments without fabricating anything.

Rules:
- Use only content from the master resume. Never invent experience, titles, or skills.
- Write in first person without using "I" — use action verbs directly.
- Sound human, clear, and confident. Not robotic or keyword-stuffed.
- Prioritize relevance over comprehensiveness.
- Keep bullet points concise: one strong idea per bullet.
- ATS-friendly: use keywords naturally from the job description, don't force them.
- If the applicant gave a reason for applying, use it to infer tone and emphasis (e.g. "pay" → lead with credibility; "love the mission" → lead with alignment; "gateway" → lead with transferable skills).

Output format: Return ONLY the resume content as structured plain text using EXACTLY these section headers on their own line (no other text before or after each header):
CONTACT
SUMMARY
EXPERIENCE
SKILLS
EDUCATION

Under CONTACT, list each field on its own line as "Label: Value".
Under EXPERIENCE, use hyphens (-) for bullet points.
Under SKILLS, group by category as "Category: skill1, skill2, skill3".
No markdown, no asterisks, no extra formatting symbols."""


def tailor_resume(master_resume: str, job_title: str, company: str,
                  job_description: str, why_applying: str = '') -> str:
    master_truncated = master_resume[:3000]
    jd_truncated = job_description[:2000]

    parts = [
        f"MASTER RESUME:\n{master_truncated}",
        f"TARGET JOB TITLE: {job_title}",
        f"TARGET COMPANY: {company}",
        f"JOB DESCRIPTION:\n{jd_truncated}",
    ]
    if why_applying and why_applying.strip():
        parts.append(f"WHY I WANT THIS ROLE (use for tone/emphasis only): {why_applying}")

    user_prompt = "\n\n".join(parts)
    user_prompt += "\n\nPlease tailor my resume for this specific role. Return only the resume content."

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def normalize_application_inputs(company: str, job_title: str) -> dict:
    """
    Correct typos, capitalization, and grammar in company name and job title.
    Returns {'company': str, 'job_title': str, 'corrected_company': bool, 'corrected_title': bool}
    """
    prompt = f"""Fix any typos, capitalization errors, or grammar issues in these job application fields.

Company name: {company}
Job title: {job_title}

Rules:
- Correct obvious typos (e.g. "googel" → "Google", "amazn" → "Amazon")
- Fix capitalization (e.g. "software engineer" → "Software Engineer", "ACME CORP" → "Acme Corp")
- Expand common abbreviations only if clearly intended (e.g. "Sr." can stay as-is)
- If a field looks correct already, return it unchanged
- Do NOT invent or guess company names you're unsure about — only fix obvious errors

Return ONLY valid JSON with no explanation, in this exact format:
{{"company": "corrected company name", "job_title": "corrected job title"}}"""

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    try:
        result = json.loads(raw)
        return {
            'company': result.get('company', company),
            'job_title': result.get('job_title', job_title),
            'corrected_company': result.get('company', company) != company,
            'corrected_title': result.get('job_title', job_title) != job_title,
        }
    except (json.JSONDecodeError, KeyError):
        return {
            'company': company,
            'job_title': job_title,
            'corrected_company': False,
            'corrected_title': False,
        }


def review_master_resume(content: str) -> dict:
    """
    Review a master resume for errors: date mismatches, formatting gaps, grammar issues.
    Returns {'corrected': str, 'changes': [str], 'has_changes': bool}
    """
    prompt = f"""You are reviewing someone's master resume to catch and fix errors before they use it for job applications. Act like a careful, supportive partner checking their work.

Look for and fix:
- Date inconsistencies or mismatches (e.g. end date before start date, overlapping dates that seem wrong, missing years)
- Job section formatting issues (e.g. missing job titles, company names without dates)
- Grammar and spelling errors
- Inconsistent tense (experience should use past tense except current role)
- Inconsistent formatting across sections
- Missing or obviously incomplete contact information

Rules:
- Do NOT rewrite or improve the content — only fix genuine errors
- Do NOT add information that isn't there
- Do NOT change the writing style or vocabulary
- If a section looks fine, leave it exactly as-is

RESUME:
{content[:4000]}

Return ONLY valid JSON in this exact format (no explanation outside the JSON):
{{
  "corrected_resume": "the full corrected resume text here",
  "changes": ["brief description of change 1", "brief description of change 2"]
}}

If no errors were found, return the original text unchanged and an empty changes array."""

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()

    # Strip markdown code fences if the model wrapped the JSON
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
        raw = raw.strip()

    try:
        result = json.loads(raw)
        corrected = result.get('corrected_resume', content)
        changes = result.get('changes', [])
        return {
            'corrected': corrected,
            'changes': changes,
            'has_changes': bool(changes) and corrected.strip() != content.strip(),
        }
    except (json.JSONDecodeError, KeyError):
        return {
            'corrected': content,
            'changes': [],
            'has_changes': False,
        }
