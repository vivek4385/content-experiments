import streamlit as st
from write_article import generate_article
from add_internal_links import add_internal_links
import json
import time

st.set_page_config(page_title="Article Generator - Multi-Client", page_icon="📝", layout="wide")

# Initialize session state
if 'clients' not in st.session_state:
    st.session_state.clients = {}
if 'rows' not in st.session_state:
    st.session_state.rows = [{'id': 0}]
if 'next_id' not in st.session_state:
    st.session_state.next_id = 1
if 'queue' not in st.session_state:
    st.session_state.queue = []
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'selected_client' not in st.session_state:
    st.session_state.selected_client = None

# Get API key from secrets (no user input needed)
try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except:
    st.error("API key not configured. Contact administrator.")
    st.stop()

# Main tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📁 Manage Clients", "📝 Generate Articles", "🔗 Add Internal Links", "✏️ AI Editor", "🔍 Brief Research", "Test"])

# TAB 1: MANAGE CLIENTS
with tab1:
    st.header("Client Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Create New Client")
        
        new_client_name = st.text_input("Client Name", placeholder="e.g., Vector, Acme Corp")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            new_company_brief = st.file_uploader("Company Brief", type=['txt'], key="new_company")
            new_icp_brief = st.file_uploader("ICP Brief", type=['txt'], key="new_icp")
        
        with col_b:
            new_guidelines = st.file_uploader("Writing Guidelines (optional)", type=['txt'], key="new_guidelines")
            new_sitemap_url = st.text_input("Sitemap URL (optional)", placeholder="https://example.com/sitemap.xml", key="new_sitemap")
        
        if st.button("➕ Create Client", type="primary"):
            if new_client_name and new_company_brief and new_icp_brief:
                st.session_state.clients[new_client_name] = {
                    'company_brief': new_company_brief.read().decode('utf-8'),
                    'icp_brief': new_icp_brief.read().decode('utf-8'),
                    'guidelines': new_guidelines.read().decode('utf-8') if new_guidelines else "",
                    'sitemap_url': new_sitemap_url.strip() if new_sitemap_url else ""
                }
                st.success(f"✅ Client '{new_client_name}' created!")
                st.rerun()
            else:
                st.error("Please provide client name, company brief, and ICP brief")
    
    with col2:
        st.subheader("Existing Clients")
        
        if st.session_state.clients:
            for client_name in st.session_state.clients.keys():
                col_x, col_y = st.columns([3, 1])
                col_x.write(f"📁 {client_name}")
                if col_y.button("🗑️", key=f"delete_{client_name}"):
                    del st.session_state.clients[client_name]
                    if st.session_state.selected_client == client_name:
                        st.session_state.selected_client = None
                    st.rerun()
        else:
            st.info("No clients yet. Create one to get started.")

# TAB 2: GENERATE ARTICLES
with tab2:
    st.header("Article Generator")
    
    # Client selector
    if not st.session_state.clients:
        st.warning("⚠️ No clients available. Go to 'Manage Clients' tab to create one.")
        st.stop()
    
    client_names = list(st.session_state.clients.keys())
    selected_client = st.selectbox(
        "Select Client",
        options=client_names,
        index=client_names.index(st.session_state.selected_client) if st.session_state.selected_client in client_names else 0
    )
    st.session_state.selected_client = selected_client
    
    st.markdown(f"**Active Client:** {selected_client}")
    st.markdown("---")
    
    # Add row button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("➕ Add Row"):
            st.session_state.rows.append({'id': st.session_state.next_id})
            st.session_state.next_id += 1
            st.rerun()
    
    # Header row
    cols = st.columns([2, 3, 1.5, 2])
    cols[0].markdown("**Title**")
    cols[1].markdown("**Article Brief**")
    cols[2].markdown("**Action**")
    cols[3].markdown("**Status**")
    
    # Render each row
    for idx, row in enumerate(st.session_state.rows):
        row_id = row['id']
        
        cols = st.columns([2, 3, 1.5, 2])
        
        # Title input
        title = cols[0].text_input(
            f"Title", 
            key=f"title_{row_id}",
            label_visibility="collapsed",
            placeholder="Article title..."
        )
        
        # Article Brief upload
        article_brief = cols[1].file_uploader(
            "Article Brief",
            type=['md', 'txt'],
            key=f"brief_{row_id}",
            label_visibility="collapsed"
        )
        
        # Generate button
        with cols[2]:
            # Check if this row has results
            if row_id in st.session_state.results:
                result = st.session_state.results[row_id]
                if result['status'] == 'complete':
                    st.success("✅ Done")
                elif result['status'] == 'error':
                    st.error("❌ Error")
            # Check if in queue
            elif row_id in st.session_state.queue:
                queue_pos = st.session_state.queue.index(row_id) + 1
                if queue_pos == 1:
                    st.info("⏳ Running")
                else:
                    st.warning(f"Queue #{queue_pos}")
            # Show generate button
            else:
                files_ready = article_brief and selected_client
                if st.button(
                    "🚀 Generate",
                    key=f"gen_{row_id}",
                    disabled=not files_ready,
                    use_container_width=True
                ):
                    # Add to queue
                    st.session_state.queue.append(row_id)
                    # Store file data in session state
                    client_data = st.session_state.clients[selected_client]
                    st.session_state[f'data_{row_id}'] = {
                        'title': title,
                        'article_brief': article_brief.read().decode('utf-8'),
                        'company_brief': client_data['company_brief'],
                        'icp_brief': client_data['icp_brief'],
                        'guidelines': client_data['guidelines']
                    }
                    st.rerun()
        
        # Status/Download column
        with cols[3]:
            if row_id in st.session_state.results:
                result = st.session_state.results[row_id]
                if result['status'] == 'complete':
                    st.download_button(
                        "📄 Download Article",
                        data=result['article'],
                        file_name=f"{title or 'article'}_{row_id}.md",
                        mime="text/markdown",
                        key=f"download_article_{row_id}",
                        use_container_width=True
                    )
                    st.download_button(
                        "📋 Download Log",
                        data=result['log'],
                        file_name=f"{title or 'article'}_{row_id}_log.txt",
                        mime="text/plain",
                        key=f"download_log_{row_id}",
                        use_container_width=True
                    )
                elif result['status'] == 'error':
                    st.caption(result['error'][:50] + "...")
    
    # Process queue
    if st.session_state.queue:
        current_row_id = st.session_state.queue[0]
        
        st.markdown("---")
        st.subheader(f"🔄 Generating Article (Row {current_row_id + 1})")
        
        # Get stored data
        data = st.session_state[f'data_{current_row_id}']
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(text, pct=None):
            status_text.text(text)
            if pct is not None:
                progress_bar.progress(pct)
        
        # Generate article
        try:
            final_article, log = generate_article(
                data['article_brief'],
                data['company_brief'],
                data['icp_brief'],
                data['guidelines'],
                api_key,
                progress_callback=update_progress
            )
            
            # Store result
            st.session_state.results[current_row_id] = {
                'status': 'complete',
                'article': final_article,
                'log': log
            }
            
            # Remove from queue
            st.session_state.queue.pop(0)
            
            # Clean up data
            del st.session_state[f'data_{current_row_id}']
            
            st.success(f"✅ Article {current_row_id + 1} complete!")
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            # Store error
            st.session_state.results[current_row_id] = {
                'status': 'error',
                'error': str(e)
            }
            
            # Remove from queue
            st.session_state.queue.pop(0)
            
            st.error(f"❌ Error: {str(e)}")
            time.sleep(2)
            st.rerun()
    
    # Show queue status in sidebar
    if st.session_state.queue:
        st.sidebar.markdown("---")
        st.sidebar.subheader("📋 Generation Queue")
        for idx, row_id in enumerate(st.session_state.queue, 1):
            if idx == 1:
                st.sidebar.write(f"🔄 Row {row_id + 1} - Generating...")
            else:
                st.sidebar.write(f"⏳ Row {row_id + 1} - Queued")

# TAB 3: ADD INTERNAL LINKS
with tab3:
    st.header("Add Internal Links")
    
    # Client selector
    if not st.session_state.clients:
        st.warning("⚠️ No clients available. Go to 'Manage Clients' tab to create one.")
        st.stop()
    
    link_client = st.selectbox(
        "Select Client (for sitemap)",
        options=list(st.session_state.clients.keys()),
        key="link_client_select"
    )
    
    client_data = st.session_state.clients[link_client]
    
    if not client_data.get('sitemap_url'):
        st.warning(f"⚠️ Client '{link_client}' has no sitemap URL. Please edit the client to add one.")
        st.stop()
    
    st.markdown(f"**Active Client:** {link_client}")
    st.markdown(f"**Sitemap:** {client_data['sitemap_url']}")
    st.markdown("---")
    
    # Initialize linking session state
    if 'link_rows' not in st.session_state:
        st.session_state.link_rows = [{'id': 0}]
    if 'next_link_id' not in st.session_state:
        st.session_state.next_link_id = 1
    if 'link_queue' not in st.session_state:
        st.session_state.link_queue = []
    if 'link_results' not in st.session_state:
        st.session_state.link_results = {}
    
    # Add row button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("➕ Add Row", key="add_link_row"):
            st.session_state.link_rows.append({'id': st.session_state.next_link_id})
            st.session_state.next_link_id += 1
            st.rerun()
    
    # Header row
    cols = st.columns([2, 2, 1.5, 1.5, 1.5, 2])
    cols[0].markdown("**Title**")
    cols[1].markdown("**Article File**")
    cols[2].markdown("**# Links**")
    cols[3].markdown("**Priority URLs**")
    cols[4].markdown("**Action**")
    cols[5].markdown("**Status**")
    
    # Render each row
    for idx, row in enumerate(st.session_state.link_rows):
        row_id = row['id']
        
        cols = st.columns([2, 2, 1.5, 1.5, 1.5, 2])
        
        # Title input
        title = cols[0].text_input(
            "Title",
            key=f"link_title_{row_id}",
            label_visibility="collapsed",
            placeholder="Article title..."
        )
        
        # Article upload
        article_file = cols[1].file_uploader(
            "Article",
            type=['md', 'txt'],
            key=f"link_article_{row_id}",
            label_visibility="collapsed"
        )
        
        # Number of links
        num_links = cols[2].number_input(
            "Links",
            min_value=1,
            max_value=20,
            value=5,
            key=f"link_num_{row_id}",
            label_visibility="collapsed"
        )
        
        # Priority URLs
        priority_urls = cols[3].text_area(
            "Priority URLs",
            key=f"link_priority_{row_id}",
            label_visibility="collapsed",
            placeholder="URLs (optional)",
            height=100
        )
        
        # Action button
        with cols[4]:
            # Check if this row has results
            if row_id in st.session_state.link_results:
                result = st.session_state.link_results[row_id]
                if result['status'] == 'complete':
                    st.success("✅ Done")
                elif result['status'] == 'error':
                    st.error("❌ Error")
            # Check if in queue
            elif row_id in st.session_state.link_queue:
                queue_pos = st.session_state.link_queue.index(row_id) + 1
                if queue_pos == 1:
                    st.info("⏳ Running")
                else:
                    st.warning(f"Queue #{queue_pos}")
            # Show add links button
            else:
                files_ready = article_file and link_client
                if st.button(
                    "🔗 Add Links",
                    key=f"link_gen_{row_id}",
                    disabled=not files_ready,
                    use_container_width=True
                ):
                    # Add to queue
                    st.session_state.link_queue.append(row_id)
                    # Store data
                    article_text = article_file.read().decode('utf-8')
                    st.session_state[f'link_data_{row_id}'] = {
                        'title': title,
                        'article_text': article_text,
                        'num_links': num_links,
                        'priority_urls': priority_urls,
                        'sitemap_url': client_data['sitemap_url']
                    }
                    st.rerun()
        
        # Status/Download column
        with cols[5]:
            if row_id in st.session_state.link_results:
                result = st.session_state.link_results[row_id]
                if result['status'] == 'complete':
                    st.download_button(
                        "📄 Download",
                        data=result['doc_bytes'],
                        file_name=f"{title or 'article'}_linked_{row_id}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"link_download_{row_id}",
                        use_container_width=True
                    )
                elif result['status'] == 'error':
                    st.caption(result['error'][:50] + "...")
    
    # Process queue
    if st.session_state.link_queue:
        current_row_id = st.session_state.link_queue[0]
        
        st.markdown("---")
        st.subheader(f"🔗 Adding Links (Row {current_row_id + 1})")
        
        # Get stored data
        data = st.session_state[f'link_data_{current_row_id}']
        
        # Progress tracking
        status_text = st.empty()
        
        def update_progress(text):
            status_text.text(text)
        
        # Add links
        try:
            doc = add_internal_links(
                article_text=data['article_text'],
                sitemap_url=data['sitemap_url'],
                num_links=data['num_links'],
                priority_urls=data['priority_urls'],
                api_key=api_key,
                progress_callback=update_progress
            )
            
            # Save to bytes
            from io import BytesIO
            doc_bytes = BytesIO()
            doc.save(doc_bytes)
            doc_bytes.seek(0)
            
            # Store result
            st.session_state.link_results[current_row_id] = {
                'status': 'complete',
                'doc_bytes': doc_bytes.getvalue()
            }
            
            # Remove from queue
            st.session_state.link_queue.pop(0)
            
            # Clean up data
            del st.session_state[f'link_data_{current_row_id}']
            
            st.success(f"✅ Links added to article {current_row_id + 1}!")
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            # Store error
            st.session_state.link_results[current_row_id] = {
                'status': 'error',
                'error': str(e)
            }
            
            # Remove from queue
            st.session_state.link_queue.pop(0)
            
            st.error(f"❌ Error: {str(e)}")
            time.sleep(2)
            st.rerun()
    
    # Show queue status in sidebar
    if st.session_state.link_queue:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔗 Linking Queue")
        for idx, row_id in enumerate(st.session_state.link_queue, 1):
            if idx == 1:
                st.sidebar.write(f"🔄 Row {row_id + 1} - Adding links...")
            else:
                st.sidebar.write(f"⏳ Row {row_id + 1} - Queued")

# TAB 5: BRIEF RESEARCH
with tab5:
    st.header("🔍 Brief Research")
    st.markdown("Research topics, generate article structure, and create writing guidelines")
    
    # Get API keys from secrets
    try:
        serpapi_key = st.secrets["SERPAPI_KEY"]
        firecrawl_key = st.secrets["FIRECRAWL_KEY"]
    except:
        st.error("⚠️ API keys not configured. Add SERPAPI_KEY and FIRECRAWL_KEY to Streamlit secrets.")
        st.stop()
    
    # Initialize research state
    if 'research_unique_headers' not in st.session_state:
        st.session_state.research_unique_headers = ""
    if 'research_brief_structure' not in st.session_state:
        st.session_state.research_brief_structure = ""
    
    # Client selector
    if not st.session_state.clients:
        st.warning("⚠️ No clients available. Create a client first for ICP/company context.")
        st.stop()
    
    research_client = st.selectbox(
        "Select Client",
        options=list(st.session_state.clients.keys()),
        key="research_client_select"
    )
    
    research_client_data = st.session_state.clients[research_client]
    
    st.markdown("---")
    
    # SECTION 1: RESEARCH TOPIC
    st.subheader("Step 1: Research Topic")
    
    keyword = st.text_input("Enter keyword/topic", placeholder="e.g., payment automation for B2B")
    
    if st.button("🔍 Research Topic", disabled=not keyword):
        with st.spinner("Researching topic..."):
            try:
                from serpapi import GoogleSearch
                from firecrawl import FirecrawlApp
                import re
                from anthropic import Anthropic
                
                # Step 1: Search Google
                st.info("Searching Google for top results...")
                params = {
                    "q": keyword,
                    "num": 10,
                    "api_key": serpapi_key
                }
                
                search = GoogleSearch(params)
                results = search.get_dict()
                
                urls = [r['link'] for r in results.get('organic_results', [])][:10]
                people_also_ask = [q.get('question', '') for q in results.get('related_questions', [])]
                
                st.success(f"Found {len(urls)} URLs and {len(people_also_ask)} PAA questions")
                
                # Step 2: Scrape each URL and extract headers
                st.info("Scraping articles and extracting headers...")
                firecrawl = FirecrawlApp(api_key=firecrawl_key)
                
                all_headers = []
                scrape_errors = []
                
                for idx, url in enumerate(urls, 1):
                    try:
                        st.text(f"Scraping {idx}/{len(urls)}: {url[:50]}...")
                        result = firecrawl.scrape(url)
                        markdown = result.markdown if hasattr(result, 'markdown') else ''
                        
                        if not markdown:
                            scrape_errors.append(f"{url}: No markdown content returned")
                            st.warning(f"No content from {url[:50]}")
                            continue
                        
                        # Debug: show first 200 chars of markdown
                        st.text(f"Got {len(markdown)} chars. Preview: {markdown[:200]}")
                
                                
                        # Extract H2 and H3 headers
                        lines = markdown.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line.startswith('## ') and not line.startswith('### '):
                                h2_title = line.replace('## ', '').strip()
                                all_headers.append(f"## {h2_title}")
                            elif line.startswith('### '):
                                h3_title = line.replace('### ', '').strip()
                                all_headers.append(f"### {h3_title}")
                        
                    except Exception as e:
                        st.warning(f"Failed to scrape {url}: {str(e)}")
                        continue
                
                if scrape_errors:
                    st.warning(f"Failed to scrape {len(scrape_errors)} URLs:")
                    for err in scrape_errors:
                        st.text(f"- {err}")
                
                if not all_headers:
                    st.error("No headers extracted from any articles. FireCrawl may be failing or articles have no H2/H3 headers.")
                    st.stop()
                
                st.success(f"Extracted {len(all_headers)} total headers from {len(urls)} articles")                
                
                # Step 3: Deduplicate with Claude
                st.info("Deduplicating headers with AI...")
                client = Anthropic(api_key=api_key)
                
                headers_text = '\n'.join(all_headers)
                paa_text = '\n'.join([f"- {q}" for q in people_also_ask])
                
                dedup_prompt = f"""You are analyzing article headers from competitor content.

ALL HEADERS FOUND:
{headers_text}

PEOPLE ALSO ASK QUESTIONS:
{paa_text}

Task:
1. Deduplicate similar/identical headers (merge synonyms and similar concepts)
2. Remove exact duplicates
3. Create a unique, consolidated list
4. Include relevant PAA questions as potential sections
5. Organize logically with H2s and H3s

Return ONLY the unique list of headers in markdown format (using ## for H2 and ### for H3). No explanations.

Unique headers:"""
                
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": dedup_prompt}]
                )
                
                unique_headers = message.content[0].text.strip()
                st.session_state.research_unique_headers = unique_headers
                
                st.success("✅ Research complete!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error during research: {str(e)}")
    
    # Display unique headers if available
    if st.session_state.research_unique_headers:
        st.markdown("### 📋 Unique Headers Found")
        with st.expander("View Headers", expanded=True):
            st.markdown(st.session_state.research_unique_headers)
        
        st.download_button(
            "📄 Download Unique Headers",
            data=st.session_state.research_unique_headers,
            file_name=f"{keyword.replace(' ', '_')}_headers.md" if keyword else "headers.md",
            mime="text/markdown"
        )
    
    st.markdown("---")
    
    # SECTION 2: GENERATE BRIEF STRUCTURE
    st.subheader("Step 2: Generate Article Brief Structure")
    st.caption("Refines headers for ICP/company fit. Auto-populated from Step 1, or paste edited version.")
    
    # Auto-populate or allow manual input
    structure_input = st.text_area(
        "Headers to refine",
        value=st.session_state.research_unique_headers,
        height=300,
        key="structure_input",
        placeholder="Paste H2/H3 structure here..."
    )
    
    if st.button("📝 Generate Brief Structure", disabled=not structure_input):
        with st.spinner("Refining structure for ICP/company fit..."):
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)
                
                refine_prompt = f"""You are refining an article outline for a specific audience and company.

CURRENT HEADERS:
{structure_input}

TARGET AUDIENCE:
{research_client_data['icp_brief']}

COMPANY CONTEXT:
{research_client_data['company_brief']}

Task:
1. Evaluate each section for relevance to the ICP
2. Rewrite headers to use ICP-specific language and pain points
3. Remove sections irrelevant to this audience
4. Add sections competitors missed but the ICP needs
5. Organize in logical order for this audience
6. Maintain H2/H3 hierarchy

Return ONLY the refined outline in markdown format (## for H2, ### for H3). No explanations.

Refined outline:"""
                
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": refine_prompt}]
                )
                
                brief_structure = message.content[0].text.strip()
                st.session_state.research_brief_structure = brief_structure
                
                st.success("✅ Brief structure generated!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error generating structure: {str(e)}")
    
    # Display brief structure if available
    if st.session_state.research_brief_structure:
        st.markdown("### 📐 Article Brief Structure")
        with st.expander("View Structure", expanded=True):
            st.markdown(st.session_state.research_brief_structure)
        
        st.download_button(
            "📄 Download Brief Structure",
            data=st.session_state.research_brief_structure,
            file_name=f"{keyword.replace(' ', '_') if keyword else 'article'}_structure.md",
            mime="text/markdown"
        )
        
        st.info("💡 You can now edit this structure in the AI Editor tab, then come back here to generate writing guidelines.")
    
    st.markdown("---")
    
    # SECTION 3: GENERATE WRITING GUIDELINES
    st.subheader("Step 3: Generate Writing Guidelines")
    st.caption("Paste your final H2/H3 structure (after editing in AI Editor if needed)")
    
    final_structure = st.text_area(
        "Final article structure",
        height=300,
        key="final_structure_input",
        placeholder="Paste final H2/H3 structure here..."
    )
    
    guidelines_keyword = st.text_input("Primary keyword (for SEO)", placeholder="e.g., payment automation", key="guidelines_keyword")
    
    if st.button("✍️ Generate Writing Guidelines", disabled=not final_structure or not guidelines_keyword):
        with st.spinner("Generating writing guidelines..."):
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)
                
                guidelines_prompt = f"""Generate concise writing guidelines for each section of this outline.

OUTLINE:
{final_structure}

ICP CONTEXT:
{research_client_data['icp_brief']}

COMPANY CONTEXT:
{research_client_data['company_brief']}

PRIMARY KEYWORD: {guidelines_keyword}

REQUIREMENTS:
1. Maximum 3 sentences per guideline
2. Introduction must focus on primary ICP pain point
3. For H2 sections that are definitional (What is X, Understanding Y, technical terms) → first sentence must clearly define the topic
4. For H2 sections that are benefit/how-to/challenge-focused → first sentence should hook with pain point or transition naturally (NO definition needed)
5. Each H2 guideline should preview what the H3 subsections will cover
6. Include specific pain points, metrics, or language from ICP context
7. Note where to naturally place keywords for SEO
8. Keep guidelines actionable and specific

FORMAT:
## [Section Header]
**Writing Guidelines:** [3 sentences maximum]

### [Subsection Header]
**Writing Guidelines:** [3 sentences maximum]

Generate guidelines now:"""
                
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=8000,
                    messages=[{"role": "user", "content": guidelines_prompt}]
                )
                
                guidelines = message.content[0].text.strip()
                
                # Combine structure + guidelines into final brief
                final_brief = f"""# Article Brief: {guidelines_keyword}

## Article Structure with Writing Guidelines

{guidelines}
"""
                
                st.success("✅ Writing guidelines generated!")
                
                # Display
                st.markdown("### 📝 Complete Article Brief")
                with st.expander("View Brief", expanded=True):
                    st.markdown(final_brief)
                
                st.download_button(
                    "📄 Download Complete Brief",
                    data=final_brief,
                    file_name=f"{guidelines_keyword.replace(' ', '_')}_brief.md",
                    mime="text/markdown",
                    type="primary"
                )
                
                st.success("✅ Brief is ready! Use this in the 'Generate Articles' tab.")
                
            except Exception as e:
                st.error(f"Error generating guidelines: {str(e)}")
    
# TAB 4: AI EDITOR
with tab4:
    st.header("✏️ AI Editor")
    st.markdown("Edit your article with AI assistance through conversation")
    
    # Initialize editor state
    if 'editor_article' not in st.session_state:
        st.session_state.editor_article = ""
    if 'editor_chat_history' not in st.session_state:
        st.session_state.editor_chat_history = []
    
    # Client selector (for context)
    if st.session_state.clients:
        editor_client = st.selectbox(
            "Select Client (for context)",
            options=list(st.session_state.clients.keys()),
            key="editor_client_select"
        )
        editor_client_data = st.session_state.clients[editor_client]
    else:
        st.warning("⚠️ No clients available. Create a client first for better AI context.")
        editor_client_data = None
    
    st.markdown("---")
    
    # Input: Upload or paste article
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file = st.file_uploader("Upload Article", type=['md', 'txt'], key="editor_upload")
        if uploaded_file and st.button("Load File"):
            st.session_state.editor_article = uploaded_file.read().decode('utf-8')
            st.session_state.editor_chat_history = []
            st.success("Article loaded!")
            st.rerun()
    
    with col2:
        if st.button("Or Paste Text"):
            st.session_state.editor_article = ""
            st.session_state.editor_chat_history = []
            st.rerun()
    
    # If no article yet, show paste area
    if not st.session_state.editor_article:
        pasted_text = st.text_area("Paste your article here", height=300, key="paste_area")
        if st.button("Start Editing") and pasted_text:
            st.session_state.editor_article = pasted_text
            st.rerun()
        st.stop()
    
    # Show current article
    st.markdown("### Current Article")
    with st.expander("View Full Article", expanded=False):
        st.markdown(st.session_state.editor_article)
    
    # Chat interface
    st.markdown("### 💬 Give Instructions")
    
    # Show chat history
    for msg in st.session_state.editor_chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Tell AI what to change (e.g., 'make the intro more concise')"):
        
        # Add user message to history
        st.session_state.editor_chat_history.append({"role": "user", "content": prompt})
        
        # Call Claude
        with st.spinner("AI is updating your article..."):
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)
                
                context_text = ""
                if editor_client_data:
                    context_text = f"""
CONTEXT - Target Audience:
{editor_client_data['icp_brief']}

CONTEXT - Company:
{editor_client_data['company_brief']}
"""
                
                ai_prompt = f"""You are editing an article based on user instructions.

CURRENT ARTICLE:
{st.session_state.editor_article}

{context_text}

USER INSTRUCTION:
{prompt}

Task: Apply the user's instruction to the article. Return the COMPLETE updated article with the changes applied. Do not add explanations, just return the updated article text.

Updated article:"""
                
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=8000,
                    messages=[{"role": "user", "content": ai_prompt}]
                )
                
                updated_article = message.content[0].text.strip()
                
                # Update article
                st.session_state.editor_article = updated_article
                
                # Add AI response to history
                st.session_state.editor_chat_history.append({
                    "role": "assistant",
                    "content": "✅ Article updated! You can continue editing or download the result."
                })
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Download button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        st.download_button(
            "📄 Download Article",
            data=st.session_state.editor_article,
            file_name="edited_article.md",
            mime="text/markdown"
        )
    
    with col2:
        if st.button("🔄 Start Over"):
            st.session_state.editor_article = ""
            st.session_state.editor_chat_history = []
            st.rerun()







