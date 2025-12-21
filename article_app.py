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
tab1, tab2, tab3 = st.tabs(["📁 Manage Clients", "📝 Generate Articles", "🔗 Add Internal Links"])

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
    
    # Initialize AI chat state
    if 'ai_selected_text' not in st.session_state:
        st.session_state.ai_selected_text = ""
    if 'ai_preview' not in st.session_state:
        st.session_state.ai_preview = ""
    if 'ai_row_id' not in st.session_state:
        st.session_state.ai_row_id = None
    
    # Main layout: content on left, AI chat on right
    col_main, col_chat = st.columns([2, 1])
    
    with col_main:
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
            
            # Action buttons
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
                # Show buttons
                else:
                    # Edit with AI button
                    if st.button("✨ Edit", key=f"edit_{row_id}", use_container_width=True, disabled=not article_file):
                        # Load article for editing
                        st.session_state.ai_row_id = row_id
                        if article_file:
                            article_text = article_file.read().decode('utf-8')
                            # Initialize current version (this is what gets edited iteratively)
                            st.session_state[f'article_current_{row_id}'] = article_text
                        st.rerun()
                    
                    # Add links button
                    files_ready = article_file and link_client
                    if st.button(
                        "🔗 Add Links",
                        key=f"link_gen_{row_id}",
                        disabled=not files_ready,
                        use_container_width=True
                    ):
                        # Add to queue
                        st.session_state.link_queue.append(row_id)
                        # Use current edited version if available, otherwise use uploaded file
                        article_text = st.session_state.get(f'article_current_{row_id}', '')
                        if not article_text and article_file:
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
        
        # Show article editor if a row is selected for editing
        if st.session_state.ai_row_id is not None:
            row_id = st.session_state.ai_row_id
            st.markdown("---")
            st.subheader(f"✏️ Editing Article (Row {row_id + 1})")
            
            # Get current version (with all edits applied so far)
            current_article = st.session_state.get(f'article_current_{row_id}', '')
            
            # Display current article (read-only for now to avoid conflicts)
            st.text_area(
                "Current Article",
                value=current_article,
                height=400,
                key=f'article_viewer_{row_id}',
                help="Copy text from here to refine with AI. This updates after each accepted change."
            )
            
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("💾 Save & Close"):
                    st.session_state.ai_row_id = None
                    st.session_state.ai_selected_text = ""
                    st.session_state.ai_preview = ""
                    st.rerun()
    
    # AI Chat Sidebar
    with col_chat:
        st.markdown("### 💬 AI Editor")
        
        if st.session_state.ai_row_id is None:
            st.info("👈 Click 'Edit' on a row to start editing with AI")
        else:
            # Selected text input
            selected_text = st.text_area(
                "Selected Text (paste here)",
                height=100,
                key="ai_selected_input",
                placeholder="Copy text from the article and paste here..."
            )
            
            # Update session state
            st.session_state.ai_selected_text = selected_text
            
            # Chat input
            instruction = st.text_input(
                "Your instruction",
                placeholder="e.g., 'make this more concise'",
                key="ai_instruction"
            )
            
            if st.button("✨ Refine", disabled=not selected_text or not instruction):
                # Call Claude to refine
                row_id = st.session_state.ai_row_id
                
                with st.spinner("AI is refining..."):
                    try:
                        from anthropic import Anthropic
                        client = Anthropic(api_key=api_key)
                        
                        prompt = f"""You are helping refine article content.

SELECTED TEXT TO REFINE:
{st.session_state.ai_selected_text}

USER INSTRUCTION:
{instruction}

CONTEXT - Target Audience:
{client_data['icp_brief']}

CONTEXT - Company:
{client_data['company_brief']}

Task: Apply the user's instruction to refine the selected text. Keep changes focused on what was requested. Return ONLY the refined text, no explanations.

Refined text:"""
                        
                        message = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=2000,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        
                        refined_text = message.content[0].text.strip()
                        st.session_state.ai_preview = refined_text
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            # Preview box
            if st.session_state.ai_preview:
                st.markdown("**AI Suggestion:**")
                st.text_area(
                    "Preview",
                    value=st.session_state.ai_preview,
                    height=150,
                    key="ai_preview_box",
                    disabled=True
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Accept", use_container_width=True):
                        # Replace selected text with refined version in current article
                        row_id = st.session_state.ai_row_id
                        current_article = st.session_state.get(f'article_current_{row_id}', '')
                        
                        # Only replace if selected text is found
                        if st.session_state.ai_selected_text in current_article:
                            updated_article = current_article.replace(
                                st.session_state.ai_selected_text,
                                st.session_state.ai_preview,
                                1
                            )
                            # Update current version with the change
                            st.session_state[f'article_current_{row_id}'] = updated_article
                            
                            # Clear state
                            st.session_state.ai_preview = ""
                            st.session_state.ai_selected_text = ""
                            
                            st.success("✅ Changes applied! Article updated.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("⚠️ Selected text not found. Copy exact text from article.")
                
                with col2:
                    if st.button("✗ Reject", use_container_width=True):
                        st.session_state.ai_preview = ""
                        st.rerun()
    
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

