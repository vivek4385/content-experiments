from anthropic import Anthropic
from serpapi import GoogleSearch
from firecrawl import FirecrawlApp
import json

def analyze_content_for_refresh(article_text, keyword, icp_brief, serpapi_key, firecrawl_key, api_key, progress_callback=None):
    """
    Analyze article and generate refresh recommendations.
    
    Args:
        article_text: Current article content
        keyword: Primary keyword to analyze against
        icp_brief: ICP context for relevance filtering
        serpapi_key: SerpAPI key
        firecrawl_key: FireCrawl key
        api_key: Anthropic API key
        progress_callback: Optional progress tracking function
    
    Returns:
        str: Recommendations in write_article.py format
    """
    
    def update_progress(text):
        if progress_callback:
            progress_callback(text)
        else:
            print(text)
    
    client = Anthropic(api_key=api_key)
    
    # Step 1: Get competitor URLs
    update_progress("Searching for top competitor articles...")
    
    params = {
        "q": keyword,
        "num": 5,
        "api_key": serpapi_key
    }
    
    search = GoogleSearch(params)
    results = search.get_dict()
    
    urls = [r['link'] for r in results.get('organic_results', [])][:5]
    update_progress(f"Found {len(urls)} competitor URLs")
    
    # Step 2: Scrape competitor H2/H3 structures
    update_progress("Scraping competitor article structures...")
    
    firecrawl = FirecrawlApp(api_key=firecrawl_key)
    competitor_structures = []
    
    for idx, url in enumerate(urls, 1):
        try:
            update_progress(f"Scraping {idx}/5: {url[:50]}...")
            result = firecrawl.scrape(url)
            markdown = result.markdown if hasattr(result, 'markdown') else ''
            
            if not markdown:
                continue
            
            # Extract H2/H3 headers
            headers = []
            lines = markdown.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('## ') and not line.startswith('### '):
                    h2_title = line.replace('## ', '').strip()
                    headers.append(f"## {h2_title}")
                elif line.startswith('### '):
                    h3_title = line.replace('### ', '').strip()
                    headers.append(f"### {h3_title}")
            
            competitor_structures.append({
                'url': url,
                'headers': '\n'.join(headers)
            })
            
        except Exception as e:
            update_progress(f"Failed to scrape {url}: {str(e)}")
            continue
    
    update_progress(f"Successfully scraped {len(competitor_structures)} competitor articles")
    
    # Step 3: Extract your article structure
    your_headers = []
    lines = article_text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('## ') and not line.startswith('### '):
            h2_title = line.replace('## ', '').strip()
            your_headers.append(f"## {h2_title}")
        elif line.startswith('### '):
            h3_title = line.replace('### ', '').strip()
            your_headers.append(f"### {h3_title}")
    
    your_structure = '\n'.join(your_headers)
    
    # Step 4: Claude Call 1 - Gap Analysis
    update_progress("Analyzing content gaps...")
    
    competitor_structures_text = '\n\n'.join([
        f"COMPETITOR {i+1} ({comp['url'][:50]}):\n{comp['headers']}"
        for i, comp in enumerate(competitor_structures)
    ])
    
    gap_prompt = f"""Analyze this article structure against competitor articles to identify gaps.

YOUR ARTICLE STRUCTURE:
{your_structure}

COMPETITOR ARTICLE STRUCTURES:
{competitor_structures_text}

Task:
1. Identify sections that competitors have but you don't (missing sections)
2. Identify sections you have that seem thinner/less comprehensive than competitors (thin sections)

Return your analysis as JSON:
{{
  "missing_sections": [
    {{"title": "Section Title", "frequency": "appears in X/5 competitors", "reason": "why it matters"}}
  ],
  "thin_sections": [
    {{"title": "Your Section Title", "issue": "what's missing compared to competitors"}}
  ]
}}

Return ONLY the JSON, no explanations."""

    gap_message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": gap_prompt}]
    )
    
    gap_analysis = gap_message.content[0].text.strip()
    # Clean JSON from potential markdown formatting
    gap_analysis = gap_analysis.replace('```json', '').replace('```', '').strip()
    
    # Step 5: Claude Call 2 - ICP Relevance Filter
    update_progress("Filtering recommendations for ICP relevance...")
    
    icp_prompt = f"""Filter these content gaps based on ICP relevance.

GAP ANALYSIS:
{gap_analysis}

YOUR ARTICLE:
{article_text}

TARGET AUDIENCE (ICP):
{icp_brief}

Task:
Determine which gaps and thin sections are HIGH PRIORITY for this ICP and which are LOW PRIORITY.

Return as JSON:
{{
  "high_priority_missing": [
    {{"title": "...", "why_important_for_icp": "..."}}
  ],
  "high_priority_thin": [
    {{"title": "...", "why_needs_enrichment": "..."}}
  ],
  "low_priority": [
    {{"title": "...", "why_not_relevant": "..."}}
  ]
}}

Return ONLY the JSON."""

    icp_message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": icp_prompt}]
    )
    
    icp_filtered = icp_message.content[0].text.strip()
    icp_filtered = icp_filtered.replace('```json', '').replace('```', '').strip()
    
    # Step 6: Claude Call 3 - Generate Recommendations with Writing Guidelines
    update_progress("Generating detailed recommendations...")
    
    recommendations_prompt = f"""Generate detailed content refresh recommendations with writing guidelines.

YOUR ARTICLE:
{article_text}

COMPETITOR STRUCTURES:
{competitor_structures_text}

FILTERED GAPS (HIGH PRIORITY):
{icp_filtered}

ICP CONTEXT:
{icp_brief}

PRIMARY KEYWORD: {keyword}

Task:
Generate specific, actionable recommendations in this EXACT format:

H2 [New Section Title] ([word count] words)
[Detailed writing guidelines: what to cover, how to structure, specific points to include, tone, examples to add, ICP pain points to address]

H3 [Section to Enrich] - ENRICH ([new word count] words)
[Current state, what's missing, specific additions needed, examples from competitors, ICP alignment needed]

Rules:
1. Use "H2" prefix for new sections to add
2. Use "H3" prefix with "- ENRICH" suffix for existing sections to expand
3. Word counts should be realistic (150-300 words typical)
4. Writing guidelines must be detailed and specific (not vague)
5. Reference competitor examples where relevant
6. Align with ICP needs explicitly
7. Only include HIGH PRIORITY items

Generate recommendations now:"""

    rec_message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=5000,
        messages=[{"role": "user", "content": recommendations_prompt}]
    )
    
    recommendations = rec_message.content[0].text.strip()
    
    update_progress("✓ Analysis complete!")
    
    return recommendations
