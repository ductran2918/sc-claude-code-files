import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date
import warnings

from data_loader import EcommerceDataLoader, load_and_process_data, categorize_delivery_speed
from business_metrics import BusinessMetricsCalculator

warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="E-commerce Business Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Uniform card heights */
    div[data-testid="metric-container"] {
        background-color: white;
        border: 1px solid #ddd;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    /* Chart containers */
    .stPlotlyChart {
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Header styling */
    .main h1 {
        color: #1f1f1f;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .main h3 {
        color: #444;
        font-weight: 500;
        margin-bottom: 1rem;
        padding-left: 1rem;
    }
    
    /* Date picker styling */
    .stDateInput > div > div {
        background-color: white;
        border-radius: 8px;
    }
    
    /* Metric styling */
    div[data-testid="metric-container"] > div {
        text-align: center;
    }
    
    /* Remove default padding from columns */
    .element-container {
        margin-bottom: 0;
    }
    
    /* Grid layout improvements */
    .row-widget.stHorizontal > div {
        padding: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and process the e-commerce data"""
    loader, processed_data = load_and_process_data('ecommerce_data/')
    return loader, processed_data

@st.cache_data
def get_date_range(loader):
    """Get the available date range from the data"""
    orders = loader.processed_data['orders']
    min_date = orders['order_purchase_timestamp'].min().date()
    max_date = orders['order_purchase_timestamp'].max().date()
    return min_date, max_date

def format_currency(value):
    """Format currency values with K/M suffixes"""
    if value >= 1000000:
        return f"${value/1000000:.1f}M"
    elif value >= 1000:
        return f"${value/1000:.0f}K"
    else:
        return f"${value:.0f}"

def calculate_trend_percentage(current_value, previous_value):
    """Calculate percentage change between two values"""
    if previous_value == 0:
        return 0
    return ((current_value - previous_value) / previous_value) * 100

def create_metric_card(title, value, delta=None, delta_color="normal"):
    """Create a metric card with optional trend indicator"""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric(
            label=title,
            value=value,
            delta=f"{delta:+.2f}%" if delta is not None else None,
            delta_color=delta_color
        )

def main():
    # Load data
    loader, processed_data = load_data()
    min_date, max_date = get_date_range(loader)
    
    # Header with title and date filter
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.title("E-commerce Business Dashboard")
    
    with col2:
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="date_filter"
        )
    
    # Handle date range selection
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range if isinstance(date_range, date) else min_date
    
    # Filter data based on selected date range
    orders = loader.processed_data['orders']
    filtered_orders = orders[
        (orders['order_purchase_timestamp'].dt.date >= start_date) & 
        (orders['order_purchase_timestamp'].dt.date <= end_date)
    ]
    
    # Create filtered sales dataset
    current_year = start_date.year
    previous_year = current_year - 1
    
    # Get data for current and previous periods
    current_data = loader.create_sales_dataset(
        year_filter=current_year,
        status_filter='delivered'
    )
    
    previous_data = loader.create_sales_dataset(
        year_filter=previous_year,
        status_filter='delivered'
    )
    
    # Apply date filtering to current data
    current_data = current_data[
        (current_data['order_purchase_timestamp'].dt.date >= start_date) & 
        (current_data['order_purchase_timestamp'].dt.date <= end_date)
    ]
    
    # Calculate previous period for comparison (same date range, previous year)
    prev_start = date(previous_year, start_date.month, start_date.day)
    prev_end = date(previous_year, end_date.month, end_date.day)
    
    previous_data = previous_data[
        (previous_data['order_purchase_timestamp'].dt.date >= prev_start) & 
        (previous_data['order_purchase_timestamp'].dt.date <= prev_end)
    ]
    
    # Calculate KPIs
    current_revenue = current_data['price'].sum()
    current_orders = current_data['order_id'].nunique()
    current_aov = current_revenue / current_orders if current_orders > 0 else 0
    
    previous_revenue = previous_data['price'].sum() if len(previous_data) > 0 else 0
    previous_orders = previous_data['order_id'].nunique() if len(previous_data) > 0 else 0
    previous_aov = previous_revenue / previous_orders if previous_orders > 0 else 0
    
    # Calculate trends
    revenue_trend = calculate_trend_percentage(current_revenue, previous_revenue)
    aov_trend = calculate_trend_percentage(current_aov, previous_aov)
    orders_trend = calculate_trend_percentage(current_orders, previous_orders)
    
    # KPI Row
    st.subheader("")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        create_metric_card(
            "Total Revenue", 
            format_currency(current_revenue),
            revenue_trend,
            "normal" if revenue_trend >= 0 else "inverse"
        )
    
    with kpi_col2:
        create_metric_card(
            "Monthly Growth",
            f"{revenue_trend:+.2f}%",
            None
        )
    
    with kpi_col3:
        create_metric_card(
            "Average Order Value",
            format_currency(current_aov),
            aov_trend,
            "normal" if aov_trend >= 0 else "inverse"
        )
    
    with kpi_col4:
        create_metric_card(
            "Total Orders",
            f"{current_orders:,}",
            orders_trend,
            "normal" if orders_trend >= 0 else "inverse"
        )
    
    st.divider()
    
    # Charts Grid (2x2 layout)
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Revenue trend line chart
        st.subheader("Revenue Trend")
        
        # Prepare monthly revenue data
        current_monthly = current_data.groupby(
            current_data['order_purchase_timestamp'].dt.to_period('M')
        )['price'].sum().reset_index()
        current_monthly['period'] = current_monthly['order_purchase_timestamp'].astype(str)
        current_monthly['type'] = 'Current Period'
        
        previous_monthly = previous_data.groupby(
            previous_data['order_purchase_timestamp'].dt.to_period('M')
        )['price'].sum().reset_index()
        previous_monthly['period'] = previous_monthly['order_purchase_timestamp'].astype(str)
        previous_monthly['type'] = 'Previous Period'
        
        # Create revenue trend chart
        fig_revenue = go.Figure()
        
        if len(current_monthly) > 0:
            fig_revenue.add_trace(go.Scatter(
                x=current_monthly['period'],
                y=current_monthly['price'],
                mode='lines+markers',
                name='Current Period',
                line=dict(color='#1f77b4', width=3)
            ))
        
        if len(previous_monthly) > 0:
            fig_revenue.add_trace(go.Scatter(
                x=previous_monthly['period'],
                y=previous_monthly['price'],
                mode='lines+markers',
                name='Previous Period',
                line=dict(color='#ff7f0e', width=3, dash='dash')
            ))
        
        fig_revenue.update_layout(
            height=400,
            xaxis_title="Month",
            yaxis_title="Revenue",
            showlegend=True,
            yaxis=dict(
                tickformat=',',
                tickprefix='$'
            ),
            xaxis=dict(showgrid=True),
            yaxis2=dict(showgrid=True)
        )
        
        st.plotly_chart(fig_revenue, use_container_width=True)
    
    with chart_col2:
        # Top 10 categories bar chart
        st.subheader("Top Categories")
        
        if 'product_category_name' in current_data.columns:
            category_revenue = current_data.groupby('product_category_name')['price'].sum().sort_values(ascending=False).head(10)
            
            fig_categories = px.bar(
                x=category_revenue.values,
                y=category_revenue.index,
                orientation='h',
                color=category_revenue.values,
                color_continuous_scale='Blues',
                text=[format_currency(x) for x in category_revenue.values]
            )
            
            fig_categories.update_layout(
                height=400,
                xaxis_title="Revenue",
                yaxis_title="Category",
                showlegend=False,
                coloraxis_showscale=False,
                yaxis={'categoryorder':'total ascending'}
            )
            
            fig_categories.update_traces(textposition='outside')
            
            st.plotly_chart(fig_categories, use_container_width=True)
        else:
            st.info("Category data not available")
    
    # Second row of charts
    chart_col3, chart_col4 = st.columns(2)
    
    with chart_col3:
        # US choropleth map
        st.subheader("Revenue by State")
        
        if 'customer_state' in current_data.columns:
            state_revenue = current_data.groupby('customer_state')['price'].sum().reset_index()
            state_revenue.columns = ['state', 'revenue']
            
            fig_map = px.choropleth(
                state_revenue,
                locations='state',
                color='revenue',
                locationmode='USA-states',
                scope='usa',
                color_continuous_scale='Blues',
                hover_data={'revenue': ':$,.0f'}
            )
            
            fig_map.update_layout(
                height=400,
                geo=dict(bgcolor='rgba(0,0,0,0)'),
                coloraxis_colorbar=dict(title="Revenue")
            )
            
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("State data not available")
    
    with chart_col4:
        # Satisfaction vs delivery time
        st.subheader("Satisfaction vs Delivery Time")
        
        if 'delivery_days' in current_data.columns and 'review_score' in current_data.columns:
            # Create delivery time buckets
            current_data_copy = current_data.copy()
            current_data_copy['delivery_bucket'] = current_data_copy['delivery_days'].apply(categorize_delivery_speed)
            
            satisfaction_delivery = current_data_copy.groupby('delivery_bucket')['review_score'].mean().reset_index()
            
            # Define bucket order
            bucket_order = ['1-3 days', '4-7 days', '8+ days', 'Unknown']
            satisfaction_delivery['delivery_bucket'] = pd.Categorical(
                satisfaction_delivery['delivery_bucket'], 
                categories=bucket_order, 
                ordered=True
            )
            satisfaction_delivery = satisfaction_delivery.sort_values('delivery_bucket')
            
            fig_satisfaction = px.bar(
                satisfaction_delivery,
                x='delivery_bucket',
                y='review_score',
                color='review_score',
                color_continuous_scale='Blues',
                text=[f"{x:.1f}" for x in satisfaction_delivery['review_score']]
            )
            
            fig_satisfaction.update_layout(
                height=400,
                xaxis_title="Delivery Time",
                yaxis_title="Average Review Score",
                showlegend=False,
                coloraxis_showscale=False,
                yaxis=dict(range=[0, 5])
            )
            
            fig_satisfaction.update_traces(textposition='outside')
            
            st.plotly_chart(fig_satisfaction, use_container_width=True)
        else:
            st.info("Delivery and review data not available")
    
    st.divider()
    
    # Bottom row cards
    bottom_col1, bottom_col2 = st.columns(2)
    
    with bottom_col1:
        # Average delivery time with trend
        if 'delivery_days' in current_data.columns:
            current_delivery = current_data['delivery_days'].mean()
            previous_delivery = previous_data['delivery_days'].mean() if len(previous_data) > 0 and 'delivery_days' in previous_data.columns else current_delivery
            delivery_trend = calculate_trend_percentage(current_delivery, previous_delivery)
            
            st.metric(
                "Average Delivery Time",
                f"{current_delivery:.1f} days",
                f"{delivery_trend:+.2f}%",
                delta_color="inverse" if delivery_trend > 0 else "normal"  # Longer delivery is bad
            )
    
    with bottom_col2:
        # Review score with stars
        if 'review_score' in current_data.columns:
            avg_review = current_data['review_score'].mean()
            stars = "⭐" * int(round(avg_review))
            
            st.metric(
                "Average Review Score",
                f"{avg_review:.1f}/5.0 {stars}",
                None
            )
        else:
            st.metric("Average Review Score", "N/A")

if __name__ == "__main__":
    main()