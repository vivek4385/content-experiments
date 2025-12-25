from anthropic import Anthropic
import re
import os
import time

def generate_article(article_brief_text, company_brief_text, icp_brief_text, writing_guidelines_text, api_key, progress_callback=None):
    """
    Generate an article from briefs using Claude AI.
    Handles both H2 and H3 sections with individual word counts.
    
    Args:
        article_brief_text: Article brief with H2/H3 sections, word counts, and guidelines
        company_brief_text: Company context
        icp_brief_text: Audience personas
        writing_guidelines_text: Global writing guidelines (optional, can be empty string)
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
    
    update_progress("Parsing article brief...")
    
    # Parse sections from brief
    def parse_brief(brief):
        """
        Parse brief into sections with structure:
        {
            'level': 'H2' or 'H3',
            'title': 'Section Title',
            'word_count': 150,
            'guidelines': 'Write this section...'
        }
        """
        sections = []
        lines = brief.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for H2 or H3 header
            if line.startswith('## H2 ') or line.startswith('### H3 '):
                level = 'H2' if line.startswith('## H2 ') else 'H3'
                
                # Extract title and word count
                # Format: "H2 Title (150 words)" or "H2 Title (150)"
                rest = line[6:].strip() if level == 'H2' else line[7:].strip()  # Remove "## H2 " or "### H3 "
                
                # Find word count in parentheses
                word_count_match = re.search(r'\((\d+)\s*(?:words?)?\)', rest)
                
                if word_count_match:
                    word_count = int(word_count_match.group(1))
                    title = rest[:word_count_match.start()].strip()
                else:
                    # No word count specified, default to 200
                    word_count = 200
                    title = rest
                
                # Get guidelines (next line(s) until next header or end)
                i += 1
                guidelines_lines = []
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith('## H2 ') or next_line.startswith('### H3 '):
                        break
                    if next_line:  # Skip empty lines
                        guidelines_lines.append(next_line)
                    i += 1
                
                guidelines = ' '.join(guidelines_lines)
                
                sections.append({
                    'level': level,
                    'title': title,
                    'word_count': word_count,
                    'guidelines': guidelines
                })
                
                continue
            
            i += 1
        
        return sections
    
    sections = parse_brief(article_brief_text)
    update_progress(f"✓ Parsed {len(sections)} sections from brief")
    
    # Log file
    log = []
    log.append(f"Article Generation Log\n{'='*50}\n")
    log.append(f"Total sections to write: {len(sections)}\n\n")
    
    # Write each section
    article_sections = []
    
    def write_section(section, index):
        """Write one section"""
        section_label = f"{section['level']}: {section['title']}"
        
        update_progress(f"Writing {section_label} ({section['word_count']} words)...")
        
        # Determine section type for prompt
        if section['level'] == 'H2':
            section_type = "an H2 section intro paragraph"
        else:
            section_type = "an H3 subsection"
        
        prompt = f"""You are writing ONE SECTION of an article. Write ONLY this section, nothing else.

FULL ARTICLE BRIEF (for context):
{article_brief_text}

COMPANY CONTEXT:
{company_brief_text}

TARGET AUDIENCE:
{icp_brief_text}

{'GLOBAL WRITING GUIDELINES:\n' + writing_guidelines_text if writing_guidelines_text else ''}

SECTION TO WRITE:
{section['level']}: {section['title']}

WORD COUNT TARGET: {section['word_count']} words

WRITING GUIDELINES FOR THIS SECTION:
{section['guidelines']}

Instructions:
- Write ONLY the body content for this section
- Do NOT include the section header (## or ###) - it will be added automatically
- Start directly with the paragraph content
- Follow the section-specific writing guidelines exactly
- Target approximately {section['word_count']} words (±10% is acceptable)
- Use markdown formatting for emphasis within the content
- This is {section_type} - write accordingly

Write the section content now:"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        section_content = message.content[0].text.strip()
        
        # Count words
        word_count = len(section_content.split())
        log.append(f"✓ Wrote {section_label} ({word_count} words, target: {section['word_count']})\n")
        
        return {
            'level': section['level'],
            'title': section['title'],
            'content': section_content
        }
    
    # Write all sections one by one
    total_sections = len(sections)
    for i, section in enumerate(sections, 1):
        written_section = write_section(section, i)
        article_sections.append(written_section)
        update_progress(f"Completed {i}/{total_sections} sections", (i / total_sections))
        time.sleep(1)  # Rate limiting
    
    # Assemble full article
    def assemble_article():
        full_article = []
        
        for section in article_sections:
            # Add header
            if section['level'] == 'H2':
                full_article.append(f"\n## {section['title']}\n")
            else:
                full_article.append(f"\n### {section['title']}\n")
            
            # Add content
            full_article.append(section['content'])
        
        return '\n'.join(full_article)
    
    final_article = assemble_article()
    
    update_progress("✓ Article assembled", 1.0)
    log.append("\n✓ Article assembled\n")
    
    update_progress("✓ Article generation complete!", 1.0)
    
    log_text = ''.join(log)
    
    return final_article, log_text


# Original command-line interface (for backward compatibility)
if __name__ == "__main__":
    # Read files from disk
    with open('article_brief.md', 'r', encoding='utf-8') as f:
        article_brief = f.read()
    
    with open('Vector Company Brief.txt', 'r', encoding='utf-8') as f:
        company_brief = f.read()
    
    with open('Vector ICP briefs.txt', 'r', encoding='utf-8') as f:
        icp_brief = f.read()
    
    writing_guidelines = ""
    if os.path.exists('writing_guidelines.txt'):
        with open('writing_guidelines.txt', 'r', encoding='utf-8') as f:
            writing_guidelines = f.read()
    
    api_key = "YOUR_API_KEY_HERE"  # Replace when testing locally
    
    # Generate article
    final_article, log = generate_article(
        article_brief, 
        company_brief, 
        icp_brief, 
        writing_guidelines, 
        api_key
    )
    
    # Save outputs
    with open('article_final.md', 'w', encoding='utf-8') as f:
        f.write(final_article)
    
    with open('article_log.txt', 'w', encoding='utf-8') as f:
        f.write(log)
    
    print("\n" + "="*50)
    print("✓ Article generation complete!")
    print(f"✓ Final article saved to: article_final.md")
    print(f"✓ Process log saved to: article_log.txt")
    print("="*50)
