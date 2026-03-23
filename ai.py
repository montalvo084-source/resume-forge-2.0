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
    prompt = f"""You are a meticulous resume proofreader. Review this resume and fix any errors. Be especially aggressive about catching date problems.

PRIORITY — Date issues to catch and fix:
- Employment dates listed in wrong order (e.g. "2022 - 2019" should be "2019 - 2022")
- End date that comes before the start date for any job
- Impossible date ranges (e.g. working somewhere before graduating)
- Jobs where the dates clearly don't make logical sense in sequence
- Missing dates on any experience or education entry
- Dates formatted inconsistently (mix of "Jan 2020" vs "2020" vs "01/2020" — standardize them)

Also fix:
- Grammar and spelling errors anywhere in the document
- Wrong tense (past jobs should use past tense, current job uses present tense)
- Job titles or company names that appear to be cut off or malformed
- Bullet points that are missing a verb or are clearly incomplete sentences
- Contact info that looks broken (e.g. email missing @ symbol, phone with wrong digit count)

Hard rules:
- Do NOT rewrite, rephrase, or improve content that is already correct
- Do NOT invent dates, companies, titles, or any missing information
- Do NOT change the structure or order of sections
- Only fix things that are clearly wrong

RESUME TO REVIEW:
{content[:4000]}

Return ONLY valid JSON (no text before or after):
{{
  "corrected_resume": "the full corrected resume text",
  "changes": ["specific description of each fix made, e.g. 'Fixed date range at Acme Corp: was 2022-2019, corrected to 2019-2022'"]
}}

If nothing needs fixing, return the original text exactly and an empty changes array."""

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
