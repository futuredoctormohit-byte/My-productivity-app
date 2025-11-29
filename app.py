import streamlit as st
import pandas as pd
import PyPDF2
import re

# --- APP CONFIGURATION ---
st.set_page_config(
    page_title="My PDF Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS FOR UI ENHANCEMENTS ---
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .stTextArea textarea {
        font-size: 16px;
    }
    .highlight {
        background-color: #ffffcc;
        padding: 2px;
        border-radius: 4px;
    }
    .step-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- DATA EXTRACTION ENGINE ---
@st.cache_data
def load_and_parse_pdfs(uploaded_files):
    """
    Extracts text from uploaded PDFs and structures it into a DataFrame.
    Ensures ZERO DATA LOSS by capturing full raw text.
    """
    data = []
    
    for uploaded_file in uploaded_files:
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            file_name = uploaded_file.name
            
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    # Clean slightly but keep raw content
                    # We store line by line to help with granular search/checklists
                    lines = text.split('\n')
                    for line_idx, line in enumerate(lines):
                        if line.strip(): # Skip empty lines
                            data.append({
                                "File": file_name,
                                "Page": i + 1,
                                "Line_Index": line_idx,
                                "Content": line.strip(),
                                "Full_Page_Text": text  # Store context
                            })
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")
            
    return pd.DataFrame(data)

def extract_action_items(df):
    """
    Heuristic parser to identify 'Actionable' items for the Checklist Mode.
    Looks for keywords common in your PDFs: 'Step', 'Action', 'Checklist', '☐', '☑'
    """
    # Regex patterns based on the documents provided (Steps, Checkboxes, Rules)
    pattern = r"^(Step \d+|Action|☐|☑|✓|•|Rule \d+|Metric)"
    
    actions = df[df['Content'].str.contains(pattern, case=False, regex=True)].copy()
    return actions

# --- MAIN APP LOGIC ---

def main():
    st.sidebar.title("🧠 PDF Knowledge Base")
    st.sidebar.markdown("---")
    
    # 1. FILE UPLOADER
    uploaded_files = st.sidebar.file_uploader(
        "Upload your PDFs here", 
        type=["pdf"], 
        accept_multiple_files=True
    )

    if not uploaded_files:
        st.info("👋 Welcome! Please upload your PDF documents to start.")
        st.markdown("### How this works:")
        st.markdown("* **Reader:** Read content page-by-page.")
        st.markdown("* **Search:** Find exact keywords across all files.")
        st.markdown("* **Checklist:** Auto-extracts steps and to-dos.")
        st.markdown("* **Ask:** Get verbatim snippets based on your queries.")
        return

    # Process Data
    with st.spinner("Ingesting Knowledge Base..."):
        df = load_and_parse_pdfs(uploaded_files)
        if df.empty:
            st.error("Could not extract text. Please check if PDFs are text-based (not scanned images).")
            return
            
    # Sidebar Navigation
    mode = st.sidebar.radio("Select Mode", ["📖 Reader", "🔍 Global Search", "✅ Interactive Checklist", "💬 Chat/Query"])
    
    st.sidebar.markdown("---")
    st.sidebar.success(f"Loaded {len(df)} lines of text from {len(uploaded_files)} files.")

    # --- MODE 1: READER ---
    if mode == "📖 Reader":
        st.header("📖 Distraction-Free Reader")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            selected_file = st.selectbox("Select Document", df['File'].unique())
            
        file_data = df[df['File'] == selected_file]
        max_page = int(file_data['Page'].max())
        
        with col1:
            page_num = st.number_input("Go to Page", min_value=1, max_value=max_page, value=1)
            
        # Display Content
        page_content = file_data[file_data['Page'] == page_num]['Full_Page_Text'].iloc[0]
        
        st.markdown("---")
        st.markdown(f"**{selected_file} - Page {page_num}**")
        st.text_area("Content", value=page_content, height=600)

    # --- MODE 2: GLOBAL SEARCH ---
    elif mode == "🔍 Global Search":
        st.header("🔍 Deep Search Engine")
        query = st.text_input("Search for any keyword (e.g., 'Dopamine', 'Step 1', 'Focus')")
        
        if query:
            # Case-insensitive search
            results = df[df['Content'].str.contains(query, case=False, regex=False)]
            
            st.markdown(f"Found **{len(results)}** matches.")
            
            for index, row in results.iterrows():
                with st.expander(f"Found in {row['File']} (Page {row['Page']})"):
                    # Highlight the term
                    highlighted_text = row['Content'].replace(query, f"**{query}**")
                    highlighted_text = highlighted_text.replace(query.lower(), f"**{query}**")
                    highlighted_text = highlighted_text.replace(query.capitalize(), f"**{query}**")
                    
                    st.markdown(f"> ... {highlighted_text} ...")
                    st.caption(f"Line {row['Line_Index']}")

    # --- MODE 3: INTERACTIVE CHECKLIST ---
    elif mode == "✅ Interactive Checklist":
        st.header("✅ Generated Productivity Tracker")
        st.info("The app automatically identified these actionable steps from your documents.")
        
        actions = extract_action_items(df)
        
        # Filter by file
        filter_file = st.selectbox("Filter by Source", ["All"] + list(df['File'].unique()))
        if filter_file != "All":
            actions = actions[actions['File'] == filter_file]

        # Display as checkboxes
        for index, row in actions.iterrows():
            # Create a unique key for session state
            key = f"{row['File']}_{row['Page']}_{row['Line_Index']}"
            
            col1, col2 = st.columns([0.05, 0.95])
            with col1:
                # Actual interactive checkbox
                st.checkbox("", key=key)
            with col2:
                st.markdown(f"**{row['Content']}**")
                st.caption(f"Source: {row['File']} | Page {row['Page']}")
            st.divider()

    # --- MODE 4: CHAT / QUERY ---
    elif mode == "💬 Chat/Query":
        st.header("💬 Ask Your Knowledge Base")
        st.markdown("Ask a question to retrieve the *exact* verbatim text block.")
        
        user_query = st.text_input("Query (e.g., 'What is the 5 second rule?')")
        
        if user_query:
            # Simple relevance scoring: Count occurrence of query words in the page text
            # We search against full pages to give context
            unique_pages = df[['File', 'Page', 'Full_Page_Text']].drop_duplicates()
            
            results = []
            query_tokens = user_query.lower().split()
            
            for index, row in unique_pages.iterrows():
                score = 0
                text_lower = row['Full_Page_Text'].lower()
                for token in query_tokens:
                    if token in text_lower:
                        score += 1
                
                if score > 0:
                    results.append({
                        "File": row['File'],
                        "Page": row['Page'],
                        "Text": row['Full_Page_Text'],
                        "Score": score
                    })
            
            # Sort by score
            results = sorted(results, key=lambda x: x['Score'], reverse=True)
            
            if results:
                st.success(f"Found relevant content in {len(results)} pages.")
                for res in results[:3]: # Show top 3 results
                    st.markdown(f"### From: {res['File']} (Page {res['Page']})")
                    st.info(res['Text'])
                    st.markdown("---")
            else:
                st.warning("No exact matches found. Try using simpler keywords.")

if __name__ == "__main__":
    main()
