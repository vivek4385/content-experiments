from anthropic import Anthropic
import re
import os
import time

def generate_article(article_brief_text, company_brief_text, icp_brief_text, writing_guidelines_text, api_key, progress_callback=None):
    """
    Generate an article from briefs using Claude AI.
    
    Args:
        article_brief_text: Article outline with H2/H3 sections
        company_brief_text: Company context
        icp_brief_text: Audience personas
        writing_guidelines_text: Tone/style guidelines (can be empty string)
        api_key: Anthropic API key
        progress_callback: Optional function to call with progress updates (text, progress_pct)
    
    Returns:
        tuple: (final_article_text, log_text)
    """
    
    def update_progress(text, pct=None):
        if progress_callback:
            progress_callback(text, pct)
        else:
            print(text)
    
    # Initialize client
    client = Anthropic(api_key=api_key)
    
    update_progress("Reading input files...")
    
    # Parse sections from brief (only H3 headers)
    def parse_sections(brief):
        sections = []
        lines = brief.split('\n')
        current_h2 = None
        
        for line in lines:
            line = line.strip()
            # Strip bold markers
            line = line.replace('**', '')
            
            # Track H2 for context
            if line.startswith('## '):
                current_h2 = line.replace('## ', '').strip()
            # Only capture H3 headers as sections to write
            elif line.startswith('### '):
                h3_title = line.replace('### ', '').strip()
                sections.append({
                    'level': 'H3',
                    'title': h3_title,
                    'parent': current_h2
                })
        
        return sections
    
    sections = parse_sections(article_brief_text)
    update_progress(f"✓ Parsed {len(sections)} H3 sections from brief")
    
    # Log file
    log = []
    log.append(f"Article Generation Log\n{'='*50}\n")
    log.append(f"Total H3 sections to write: {len(sections)}\n\n")
    
    # Write each section
    article_sections = {}
    
    def write_section(section, attempt=1):
        section_key = f"{section['level']}: {section['title']}"
        
        update_progress(f"Writing {section_key} (attempt {attempt})...")
        
        prompt = f"""You are writing ONE SECTION of an article. Write ONLY this section, nothing else.

ARTICLE BRIEF (for context):
{article_brief_text}

COMPANY CONTEXT:
{company_brief_text}

TARGET AUDIENCE:
{icp_brief_text}

{'WRITING GUIDELINES:\n' + writing_guidelines_text if writing_guidelines_text else ''}

SECTION TO WRITE:
{section['level']}: {section['title']}
(This is a subsection under: {section['parent']})

Instructions:
- Write ONLY the body content for this H3 section
- The section header will be added automatically - do NOT include it
- Start directly with the paragraph content
- Follow the structure and guidance in the article brief for this section
- Match the tone and style specified in the guidelines
- If word count is specified in the brief for this section, follow it
- Use markdown formatting for any sub-bullets or emphasis within the content
- Write in a professional, clear style appropriate for the target audience

Write the section content now:"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        section_content = message.content[0].text.strip()
        log.append(f"✓ Wrote {section_key} (attempt {attempt})\n")
        
        return section_content
    
    # Write all H3 sections
    total_sections = len(sections)
    for i, section in enumerate(sections, 1):
        section_key = f"{section['level']}: {section['title']}"
        article_sections[section_key] = write_section(section)
        update_progress(f"Completed {i}/{total_sections} sections", (i / total_sections) * 0.7)
        time.sleep(1)
    
    # Assemble full article (add H2 headers with H3 content)
    def assemble_article():
        full_article = []
        current_h2 = None
        
        for section in sections:
            # Add H2 header when it changes
            if section['parent'] != current_h2:
                current_h2 = section['parent']
                full_article.append(f"\n## {current_h2}\n")
            
            # Add H3 header and content
            section_key = f"{section['level']}: {section['title']}"
            full_article.append(f"\n### {section['title']}\n")
            full_article.append(article_sections[section_key])
        
        return '\n'.join(full_article)
    
    draft_article = assemble_article()
    
    update_progress("✓ Draft article assembled", 0.75)
    log.append("\n✓ Draft article assembled\n\n")
    
    # Review the article
    update_progress("Reviewing article against requirements...", 0.80)
    
    review_prompt = f"""Review this article against the brief. Check for:

1. All H3 sections from the brief are present
2. Word count targets reasonably met (within 20% is acceptable)
3. No duplicate H3 sections
4. Content quality and accuracy

ARTICLE BRIEF:
{article_brief_text}

{'WRITING GUIDELINES:\n' + writing_guidelines_text if writing_guidelines_text else ''}

ARTICLE TO REVIEW:
{draft_article}

Respond in this format:

STATUS: [PASS or FAIL]

ISSUES: [If FAIL, list specific H3 sections that need revision and why. If PASS, write "None"]

Focus on major issues only."""

    review_message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": review_prompt
        }]
    )
    
    review_result = review_message.content[0].text.strip()
    log.append("REVIEW RESULTS:\n")
    log.append(review_result + "\n\n")
    
    update_progress("Review complete", 0.85)
    
    # Check if revisions needed
    if "STATUS: FAIL" in review_result:
        update_progress("⚠ Issues found. Rewriting affected sections...", 0.85)
        
        issues_section = review_result.split("ISSUES:")[1] if "ISSUES:" in review_result else ""
        
        retry_count = 0
        max_review_cycles = 2
        
        while retry_count < max_review_cycles and "STATUS: FAIL" in review_result:
            retry_count += 1
            log.append(f"\n--- REVISION CYCLE {retry_count} ---\n")
            
            for section in sections:
                section_key = f"{section['level']}: {section['title']}"
                
                if section['title'].lower() in issues_section.lower():
                    update_progress(f"Rewriting {section_key}...")
                    article_sections[section_key] = write_section(section, attempt=retry_count+1)
                    time.sleep(1)
            
            draft_article = assemble_article()
            
            review_message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": review_prompt.replace("ARTICLE TO REVIEW:", f"ARTICLE TO REVIEW (Revision {retry_count}):")
                }]
            )
            
            review_result = review_message.content[0].text.strip()
            log.append(f"Review after revision {retry_count}:\n{review_result}\n\n")
            
            if "STATUS: PASS" in review_result:
                update_progress(f"✓ Article passed review after {retry_count} revision(s)", 0.95)
                break
        
        if retry_count >= max_review_cycles and "STATUS: FAIL" in review_result:
            update_progress(f"⚠ Article has issues after {max_review_cycles} attempts. Saving for manual review.", 0.95)
            log.append(f"\n⚠ Maximum revision cycles reached. Saving for manual review.\n")
    
    update_progress("✓ Article generation complete!", 1.0)
    
    log_text = ''.join(log)
    
    return draft_article, log_text
