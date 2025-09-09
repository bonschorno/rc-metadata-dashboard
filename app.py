import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from pathlib import Path
from api_client import ETHResearchCollectionAPI
from publication_stats import PublicationStatsAPI
import time

st.set_page_config(
    page_title="Research Collection Metadata",
    page_icon="📊",
    layout="wide"
)

def check_authentication():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    return st.session_state.authenticated

def authenticate_user(api_key, group_id):
    """Authenticate and test API connection."""
    if api_key and group_id and len(group_id) == 5 and group_id.isdigit():
        try:
            # Test API connection with real credentials
            test_client = ETHResearchCollectionAPI(api_key=api_key, group_identifier=group_id)
            # Try fetching just 1 item to test the connection
            test_data = test_client.fetch_publications(max_items=1)
            if test_data:
                st.session_state.authenticated = True
                st.session_state.api_key = api_key
                st.session_state.group_id = group_id
                return True
        except Exception as e:
            st.error(f"API connection failed: {str(e)}")
            return False
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
    
    st.info("💡 Enter your ETH Research Collection API key and 5-digit group ID (e.g., 09746).")
    st.stop()

st.title("📊 Research Collection Metadata")
st.markdown("---")

with st.sidebar:
    st.success(f"✅ Authenticated (Group: {st.session_state.group_id})")
    if st.button("Logout"):
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.api_key = None
        old_group_id = st.session_state.group_id
        st.session_state.group_id = None
        
        # Clear the cache for the old group
        try:
            st.cache_data.clear()
        except:
            pass
        
        st.rerun()
    st.markdown("---")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(group_id):
    """Load data from API or cache - specific to group ID."""
    # Create group-specific data directory
    data_dir = Path(f'data/group_{group_id}')
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we have recent cached data (less than 1 hour old)
    cache_files = [
        data_dir / 'monthly_visits.csv',
        data_dir / 'publication_statistics.csv', 
        data_dir / 'country_statistics.csv'
    ]
    
    # Check if all cache files exist and are recent
    use_cache = all(f.exists() for f in cache_files)
    if use_cache:
        # Check if files are less than 1 hour old
        oldest_time = min(f.stat().st_mtime for f in cache_files)
        if time.time() - oldest_time > 3600:  # 1 hour in seconds
            use_cache = False
    
    if use_cache:
        # Load from existing files
        monthly_visits = pd.read_csv(cache_files[0])
        publication_stats = pd.read_csv(cache_files[1])
        country_stats = pd.read_csv(cache_files[2])
    else:
        # Fetch fresh data from API
        with st.spinner('Fetching fresh data from API...'):
            try:
                # Initialize API clients
                pub_client = ETHResearchCollectionAPI(
                    api_key=st.session_state.api_key,
                    group_identifier=st.session_state.group_id
                )
                stats_client = PublicationStatsAPI(api_key=st.session_state.api_key)
                
                # Fetch publications metadata
                st.info("Fetching publication metadata...")
                df_publications = pub_client.fetch_and_save(output_dir=str(data_dir), max_items=50)  # Limit for testing
                
                # Get UUIDs and titles for statistics fetching
                uuids = df_publications['uuid'].tolist()
                titles = df_publications['name'].tolist()
                
                # Fetch statistics for each publication
                st.info(f"Fetching statistics for {len(uuids)} publications...")
                stats_list = stats_client.fetch_multiple_stats(uuids, titles, delay=0.5)
                
                # Save statistics to CSV files
                df_main, df_monthly, df_countries = stats_client.save_statistics(stats_list, output_dir=str(data_dir))
                
                # Load the saved files
                monthly_visits = df_monthly
                publication_stats = df_main
                country_stats = df_countries
                
                st.success("✅ Data successfully fetched and cached!")
                
            except Exception as e:
                st.error(f"Error fetching data: {str(e)}")
                # Fall back to any existing data
                if all(f.exists() for f in cache_files):
                    st.warning("Using previously cached data...")
                    monthly_visits = pd.read_csv(cache_files[0])
                    publication_stats = pd.read_csv(cache_files[1])
                    country_stats = pd.read_csv(cache_files[2])
                else:
                    raise Exception("No cached data available and API fetch failed.")
    
    # Convert month column to YYYY-MM format
    month_map = {
        'January': '01', 'February': '02', 'March': '03', 'April': '04',
        'May': '05', 'June': '06', 'July': '07', 'August': '08',
        'September': '09', 'October': '10', 'November': '11', 'December': '12'
    }
    
    # Parse month and year from the month column
    monthly_visits['month_year'] = monthly_visits['month'].apply(
        lambda x: f"{x.split()[1]}-{month_map[x.split()[0]]}"
    )
    
    # Transform monthly_visits into views format (item, month1, month2, ...)
    views_pivot = monthly_visits.pivot_table(
        index='title', 
        columns='month_year', 
        values='visits', 
        fill_value=0
    )
    views_pivot = views_pivot.reset_index()
    views_pivot.rename(columns={'title': 'item'}, inplace=True)
    
    # For downloads, use publication_statistics total_downloads
    # Create a simplified downloads dataframe with same structure as views
    downloads_pivot = views_pivot.copy()
    
    # Get total downloads for each item from publication_statistics
    downloads_map = dict(zip(publication_stats['title'], publication_stats['total_downloads']))
    
    # For each item, distribute downloads proportionally to views
    for idx, row in downloads_pivot.iterrows():
        item_name = row['item']
        total_downloads = downloads_map.get(item_name, 0)
        
        # Get views for this item (excluding the 'item' column)
        item_views = row[1:].values
        total_views = item_views.sum()
        
        if total_views > 0:
            # Distribute downloads proportionally to views
            downloads_distribution = (item_views / total_views) * total_downloads
            downloads_pivot.iloc[idx, 1:] = downloads_distribution.astype(int)
        else:
            # If no views, set downloads to 0
            downloads_pivot.iloc[idx, 1:] = 0
    
    return downloads_pivot, views_pivot, country_stats

downloads_df, views_df, country_stats = load_data(st.session_state.group_id)

with st.sidebar:
    st.header("📋 Dashboard Controls")
    
    view_type = st.radio(
        "Select Data View:",
        ["Overview", "Individual Item Analysis", "Time Series Comparison", "Top Performers", "Geographic Distribution"]
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
    
    downloads_total = int(downloads_df.iloc[:, 1:].sum().sum())
    views_total = int(views_df.iloc[:, 1:].sum().sum())
    
    with col1:
        st.metric("Total Downloads", f"{downloads_total:,d}")
    with col2:
        st.metric("Total Views", f"{views_total:,d}")
    
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
        fig_downloads.update_traces(line_color='#1f77b4', line_width=3, hovertemplate='Month: %{x}<br>Total Downloads: %{y:.0f}<extra></extra>')
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
        fig_views.update_traces(line_color='#ff7f0e', line_width=3, hovertemplate='Month: %{x}<br>Total Views: %{y:.0f}<extra></extra>')
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
    
    fig_combined.update_traces(line_width=3, hovertemplate='%{y:.0f}<extra></extra>')
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
        st.metric("Total Downloads", f"{int(item_downloads.sum()):,d}")
    with col2:
        st.metric("Total Views", f"{int(item_views.sum()):,d}")
    with col3:
        avg_downloads = item_downloads.mean()
        st.metric("Avg Monthly Downloads", f"{avg_downloads:.0f}")
    with col4:
        avg_views = item_views.mean()
        st.metric("Avg Monthly Views", f"{avg_views:.0f}")
    
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
                name=item[:50] + "..." if len(item) > 50 else item,
                hovertemplate='%{y:.0f}<extra></extra>'
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
                name=item[:50] + "..." if len(item) > 50 else item,
                hovertemplate='%{y:.0f}<extra></extra>'
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
        hovertemplate='%{x:.0f}<extra></extra>'  # Remove 'Item' from hover
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
        hovertemplate='%{x:.0f}<extra></extra>'  # Remove 'Item' from hover
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

elif view_type == "Geographic Distribution":
    st.subheader("🌍 Geographic Distribution")
    
    # Add item selector
    selected_item = st.selectbox(
        "Select a publication to analyze:",
        ['All Publications'] + sorted(country_stats['title'].unique().tolist()),
        key='geo_item_selector'
    )
    
    # Filter country data based on selection
    if selected_item == 'All Publications':
        filtered_country_stats = country_stats
        title_text = "All Publications - Geographic Distribution"
    else:
        filtered_country_stats = country_stats[country_stats['title'] == selected_item]
        title_text = f"{selected_item[:80]}..."
    
    # Aggregate country data
    country_totals = filtered_country_stats.groupby(['country_code', 'country'])['visits'].sum().reset_index()
    country_totals = country_totals.sort_values('visits', ascending=False)
    
    # Display statistics for selected item
    if selected_item != 'All Publications':
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Countries", f"{len(country_totals):,}")
        with col2:
            st.metric("Total Visits", f"{country_totals['visits'].sum():,}")
        with col3:
            st.metric("Top Country", country_totals.iloc[0]['country'] if not country_totals.empty else "N/A")
        with col4:
            top_visits = country_totals.iloc[0]['visits'] if not country_totals.empty else 0
            st.metric("Top Country Visits", f"{top_visits:,}")
        st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # World map using plotly
        # Ensure visits column is numeric
        country_totals['visits'] = pd.to_numeric(country_totals['visits'])
        
        fig_map = px.choropleth(
            country_totals,
            locations='country',  # Use country names directly
            locationmode='country names',
            color='visits',
            hover_name='country',
            hover_data={'visits': ':.0f'},  # Format as integer
            color_continuous_scale='Blues',
            title=title_text,
            labels={'visits': 'Total Visits'},
            range_color=[0, country_totals['visits'].max()] if not country_totals.empty else [0, 1]
        )
        fig_map.update_layout(
            height=500,
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type='natural earth'
            )
        )
        st.plotly_chart(fig_map, use_container_width=True)
    
    with col2:
        # Top 15 countries
        top_countries = country_totals.head(15)
        
        fig_countries = px.bar(
            top_countries,
            x='visits',
            y='country',
            orientation='h',
            title="Top 15 Countries by Visits",
            labels={'visits': 'Total Visits', 'country': 'Country'},
            color='visits',
            color_continuous_scale='Blues'  # Match map color scheme
        )
        fig_countries.update_layout(
            height=500,
            yaxis={'categoryorder': 'total ascending'},
            showlegend=False,
            coloraxis_showscale=False  # Hide color scale bar
        )
        # Format hover template to show integers
        fig_countries.update_traces(hovertemplate='%{y}<br>Total Visits: %{x:.0f}<extra></extra>')
        st.plotly_chart(fig_countries, use_container_width=True)
    
    # Detailed country table
    st.subheader("📊 Detailed Country Statistics")
    
    # Add search functionality
    search_country = st.text_input("🔍 Search countries:", placeholder="Enter country name...")
    
    filtered_countries = country_totals.copy()
    if search_country:
        filtered_countries = filtered_countries[
            filtered_countries['country'].str.contains(search_country, case=False, na=False)
        ]
    
    # Display table
    st.dataframe(
        filtered_countries[['country', 'country_code', 'visits']].reset_index(drop=True),
        use_container_width=True,
        column_config={
            'country': st.column_config.TextColumn('Country', width='large'),
            'country_code': st.column_config.TextColumn('Code', width='small'),
            'visits': st.column_config.NumberColumn('Total Visits', format='%d')
        },
        hide_index=True
    )
    
    st.info(f"Showing {len(filtered_countries)} of {len(country_totals)} countries")

st.markdown("---")
st.caption("Dashboard created with [Streamlit](https://streamlit.io/) • Data from [ETH's Research Collection](https://www.research-collection.ethz.ch/home)")