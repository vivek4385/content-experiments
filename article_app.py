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
    
    st.markdown(f"**Sitemap:** {client_data['sitemap_url']}")
    st.markdown("---")
    
    # Input section
    col1, col2 = st.columns(2)
    
    with col1:
        article_file = st.file_uploader("Upload Article", type=['md', 'txt'], help="The article to add links to")
        num_links = st.number_input("Number of Links", min_value=1, max_value=20, value=5)
    
    with col2:
        priority_urls = st.text_area(
            "Priority URLs (optional)", 
            placeholder="https://example.com/page1\nhttps://example.com/page2",
            help="One URL per line. These will be prioritized if contextually relevant."
        )
    
    # Generate button
    if st.button("🔗 Add Internal Links", type="primary", disabled=not article_file):
        
        # Read article
        article_text = article_file.read().decode('utf-8')
        
        # Progress tracking
        status_text = st.empty()
        
        def update_progress(text):
            status_text.text(text)
        
        # Add links
        try:
            doc = add_internal_links(
                article_text=article_text,
                sitemap_url=client_data['sitemap_url'],
                num_links=num_links,
                priority_urls=priority_urls,
                api_key=api_key,
                progress_callback=update_progress
            )
            
            # Save to bytes
            from io import BytesIO
            doc_bytes = BytesIO()
            doc.save(doc_bytes)
            doc_bytes.seek(0)
            
            st.success("✅ Internal links added successfully!")
            
            # Download button
            st.download_button(
                label="📄 Download Linked Article",
                data=doc_bytes.getvalue(),
                file_name="article_with_links.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
