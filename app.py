import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="GHE: Research Collection Metadata",
    page_icon="📊",
    layout="wide"
)

def check_authentication():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    return st.session_state.authenticated

def authenticate_user(api_key, group_id):
    if api_key and group_id and len(group_id) == 5 and group_id.isdigit():
        st.session_state.authenticated = True
        st.session_state.api_key = api_key
        st.session_state.group_id = group_id
        return True
    return False

if not check_authentication():
    st.title("🔐 Authentication Required")
    st.markdown("Please enter your credentials to access the dashboard.")
    
    with st.form("auth_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            api_key = st.text_input(
                "API Key", 
                type="password",
                placeholder="Enter your API key",
                help="Your secure API key for accessing the dashboard"
            )
        
        with col2:
            group_id = st.text_input(
                "Group ID", 
                placeholder="12345",
                help="Your 5-digit group identifier (e.g., 12345)",
                max_chars=5
            )
        
        submitted = st.form_submit_button("Access Dashboard", use_container_width=True)
        
        if submitted:
            if not api_key:
                st.error("Please provide an API key")
            elif not group_id:
                st.error("Please provide a Group ID")
            elif len(group_id) != 5 or not group_id.isdigit():
                st.error("Group ID must be exactly 5 digits")
            elif authenticate_user(api_key, group_id):
                st.success("Authentication successful! Loading dashboard...")
                st.rerun()
            else:
                st.error("Authentication failed. Please check your credentials.")
    
    st.info("💡 For this demo, enter any API key and group ID to access the dashboard.")
    st.stop()

st.title("📊 GHE: Research Collection Metadata")
st.markdown("---")

with st.sidebar:
    st.success(f"✅ Authenticated (Group: {st.session_state.group_id})")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.api_key = None
        st.session_state.group_id = None
        st.rerun()
    st.markdown("---")

@st.cache_data
def load_data():
    downloads_df = pd.read_csv('data/downloads.csv')
    views_df = pd.read_csv('data/views.csv')
    return downloads_df, views_df

downloads_df, views_df = load_data()

with st.sidebar:
    st.header("📋 Dashboard Controls")
    
    view_type = st.radio(
        "Select Data View:",
        ["Overview", "Individual Item Analysis", "Time Series Comparison", "Top Performers"]
    )
    
    st.markdown("---")
    st.info(f"Total Items: {len(downloads_df)}")

def prepare_time_series_data(df, metric_name):
    date_columns = [col for col in df.columns if col != 'item']
    melted = df.melt(id_vars=['item'], value_vars=date_columns, 
                     var_name='date', value_name=metric_name)
    melted['date'] = pd.to_datetime(melted['date'], format='%Y-%m')
    return melted

if view_type == "Overview":
    col1, col2 = st.columns(2)
    
    downloads_total = downloads_df.iloc[:, 1:].sum().sum()
    views_total = views_df.iloc[:, 1:].sum().sum()
    
    with col1:
        st.metric("Total Downloads", f"{downloads_total:,}")
    with col2:
        st.metric("Total Views", f"{views_total:,}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Downloads Over Time")
        downloads_by_month = downloads_df.iloc[:, 1:].sum()
        fig_downloads = px.line(
            x=pd.to_datetime(downloads_by_month.index, format='%Y-%m'),
            y=downloads_by_month.values,
            labels={'x': 'Month', 'y': 'Total Downloads'},
            line_shape='spline'
        )
        fig_downloads.update_traces(line_color='#1f77b4', line_width=3)
        fig_downloads.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_downloads, use_container_width=True)
    
    with col2:
        st.subheader("👁️ Views Over Time")
        views_by_month = views_df.iloc[:, 1:].sum()
        fig_views = px.line(
            x=pd.to_datetime(views_by_month.index, format='%Y-%m'),
            y=views_by_month.values,
            labels={'x': 'Month', 'y': 'Total Views'},
            line_shape='spline'
        )
        fig_views.update_traces(line_color='#ff7f0e', line_width=3)
        fig_views.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_views, use_container_width=True)
    
    st.subheader("📊 Combined Metrics")
    
    # Prepare data for px.line
    dates = pd.to_datetime(downloads_by_month.index, format='%Y-%m')
    combined_df = pd.DataFrame({
        'Month': dates.tolist() + dates.tolist(),
        'Count': downloads_by_month.values.tolist() + views_by_month.values.tolist(),
        'Metric': ['Downloads'] * len(dates) + ['Views'] * len(dates)
    })
    
    fig_combined = px.line(
        combined_df,
        x='Month',
        y='Count',
        color='Metric',
        labels={'Count': 'Value'},
        line_shape='spline'
    )
    
    fig_combined.update_traces(line_width=3)
    fig_combined.update_layout(height=500, hovermode='x unified')
    
    st.plotly_chart(fig_combined, use_container_width=True)

elif view_type == "Individual Item Analysis":
    st.subheader("🔍 Individual Item Analysis")
    
    selected_item = st.selectbox(
        "Select an item to analyze:",
        downloads_df['item'].tolist()
    )
    
    item_downloads = downloads_df[downloads_df['item'] == selected_item].iloc[:, 1:].values[0]
    item_views = views_df[views_df['item'] == selected_item].iloc[:, 1:].values[0]
    
    # Find the range of dates with actual data
    dates = pd.to_datetime([col for col in downloads_df.columns if col != 'item'], format='%Y-%m')
    combined_data = item_downloads + item_views
    non_zero_indices = [i for i, val in enumerate(combined_data) if val > 0]
    
    if non_zero_indices:
        first_idx = non_zero_indices[0]
        last_idx = non_zero_indices[-1]
        dates_filtered = dates[first_idx:last_idx+1]
        downloads_filtered = item_downloads[first_idx:last_idx+1]
        views_filtered = item_views[first_idx:last_idx+1]
    else:
        dates_filtered = dates
        downloads_filtered = item_downloads
        views_filtered = item_views
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Downloads", f"{item_downloads.sum():,}")
    with col2:
        st.metric("Total Views", f"{item_views.sum():,}")
    with col3:
        avg_downloads = item_downloads.mean()
        st.metric("Avg Monthly Downloads", f"{avg_downloads:.1f}")
    with col4:
        avg_views = item_views.mean()
        st.metric("Avg Monthly Views", f"{avg_views:.1f}")
    
    st.markdown("---")
    
    fig = make_subplots(rows=2, cols=1, 
                       subplot_titles=("Downloads", "Views"),
                       vertical_spacing=0.15)
    
    fig.add_trace(
        go.Bar(x=dates_filtered, y=downloads_filtered, name='Downloads',
              marker_color='#1f77b4'),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(x=dates_filtered, y=views_filtered, name='Views',
              marker_color='#ff7f0e'),
        row=2, col=1
    )
    
    fig.update_xaxes(title_text="Month", row=2, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=2, col=1)
    fig.update_layout(height=700, showlegend=False,
                     title_text=f"Metrics for: {selected_item[:80]}...")
    
    st.plotly_chart(fig, use_container_width=True)

elif view_type == "Time Series Comparison":
    st.subheader("📈 Time Series Comparison")
    
    num_items = st.slider("Number of items to compare:", 2, 10, 5)
    
    downloads_totals = downloads_df.set_index('item').sum(axis=1).sort_values(ascending=False)
    top_items = downloads_totals.head(num_items).index.tolist()
    
    selected_items = st.multiselect(
        "Select items to compare (or use top performers):",
        downloads_df['item'].tolist(),
        default=top_items[:3]
    )
    
    if selected_items:
        dates = pd.to_datetime([col for col in downloads_df.columns if col != 'item'], format='%Y-%m')
        
        st.subheader("Downloads Comparison")
        fig_downloads = go.Figure()
        
        for item in selected_items:
            item_data = downloads_df[downloads_df['item'] == item].iloc[:, 1:].values[0]
            fig_downloads.add_trace(go.Scatter(
                x=dates, y=item_data,
                mode='lines+markers',
                name=item[:50] + "..." if len(item) > 50 else item
            ))
        
        fig_downloads.update_layout(
            xaxis_title="Month",
            yaxis_title="Downloads",
            height=400,
            hovermode='x unified'
        )
        st.plotly_chart(fig_downloads, use_container_width=True)
        
        st.subheader("Views Comparison")
        fig_views = go.Figure()
        
        for item in selected_items:
            item_data = views_df[views_df['item'] == item].iloc[:, 1:].values[0]
            fig_views.add_trace(go.Scatter(
                x=dates, y=item_data,
                mode='lines+markers',
                name=item[:50] + "..." if len(item) > 50 else item
            ))
        
        fig_views.update_layout(
            xaxis_title="Month",
            yaxis_title="Views",
            height=400,
            hovermode='x unified'
        )
        st.plotly_chart(fig_views, use_container_width=True)

elif view_type == "Top Performers":
    st.subheader("🏆 Top Performing Items")
    
    top_n = st.slider("Number of top items to show:", 5, 20, 10)
    
    st.subheader("Top by Downloads")
    downloads_totals = downloads_df.set_index('item').sum(axis=1).sort_values(ascending=False)
    top_downloads = downloads_totals.head(top_n)
    
    fig_top_downloads = px.bar(
        y=top_downloads.index[::-1],  # Reverse order to show top items at the top
        x=top_downloads.values[::-1],
        orientation='h',
        labels={'x': 'Total Downloads', 'y': ''}
    )
    fig_top_downloads.update_traces(
        marker_color='#1f77b4',
        hovertemplate='%{x}<extra></extra>'  # Remove 'Item' from hover
    )
    fig_top_downloads.update_layout(height=400 + (top_n * 20), showlegend=False)
    fig_top_downloads.update_yaxes(tickmode='linear')
    st.plotly_chart(fig_top_downloads, use_container_width=True)
    
    st.subheader("Top by Views")
    views_totals = views_df.set_index('item').sum(axis=1).sort_values(ascending=False)
    top_views = views_totals.head(top_n)
    
    fig_top_views = px.bar(
        y=top_views.index[::-1],  # Reverse order to show top items at the top
        x=top_views.values[::-1],
        orientation='h',
        labels={'x': 'Total Views', 'y': ''}
    )
    fig_top_views.update_traces(
        marker_color='#ff7f0e',
        hovertemplate='%{x}<extra></extra>'  # Remove 'Item' from hover
    )
    fig_top_views.update_layout(height=400 + (top_n * 20), showlegend=False)
    fig_top_views.update_yaxes(tickmode='linear')
    st.plotly_chart(fig_top_views, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📊 Top Items Table")
    
    top_items_df = pd.DataFrame({
        'Item': downloads_totals.head(top_n).index,
        'Total Downloads': downloads_totals.head(top_n).values,
        'Total Views': [views_df[views_df['item'] == item].iloc[:, 1:].sum().sum() 
                       for item in downloads_totals.head(top_n).index],
    })
    
    st.dataframe(
        top_items_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Item": st.column_config.TextColumn("Item", width="large"),
            "Total Downloads": st.column_config.NumberColumn("Downloads", format="%d"),
            "Total Views": st.column_config.NumberColumn("Views", format="%d")
        }
    )

st.markdown("---")
st.caption("Dashboard created with Streamlit • Data from Research Collection Metadata")