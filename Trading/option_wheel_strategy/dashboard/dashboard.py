"""
Dashboard for Options Wheel Strategy.
Provides web-based monitoring and configuration interface.
"""
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyDashboard:
    """Web-based dashboard for monitoring and controlling the options wheel strategy."""
    
    def __init__(self):
        """Initialize the dashboard."""
        st.set_page_config(
            page_title="Options Wheel Strategy Dashboard",
            page_icon="📊",
            layout="wide"
        )
    
    def render_header(self):
        """Render the dashboard header."""
        st.title("📊 Options Wheel Strategy Dashboard")
        st.markdown("---")
        
        # Display key metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Portfolio Value", "₹1,250,000", "+2.3%")
        
        with col2:
            st.metric("Daily P&L", "₹12,500", "+₹1,200")
        
        with col3:
            st.metric("Active Positions", "8", "2")
        
        with col4:
            st.metric("Win Rate", "68.5%", "+3.2%")
    
    def render_portfolio_overview(self):
        """Render portfolio overview section."""
        st.subheader("Portfolio Overview")
        
        # Create sample portfolio data
        portfolio_data = pd.DataFrame({
            'Symbol': ['NIFTY24JAN20000CE', 'NIFTY24JAN19500PE', 'NIFTY24FEB19800CE', 
                      'NIFTY24FEB19200PE', 'NIFTY24MAR20500CE', 'NIFTY24MAR19000PE',
                      'NIFTY-I', 'NIFTY-I'],
            'Type': ['Short Call', 'Short Put', 'Short Call', 'Short Put', 
                    'Short Call', 'Short Put', 'Long', 'Long'],
            'Quantity': [-50, -50, -50, -50, -50, -50, 25, 25],
            'Avg Price': [150.50, 120.25, 180.75, 95.50, 135.25, 110.00, 19500, 19200],
            'Current': [140.25, 110.75, 170.50, 85.25, 125.75, 105.50, 19650, 19325],
            'P&L': [51250, 47500, 51250, 47500, 47500, 45000, 37500, 31250],
            'Days to Expiry': [15, 15, 45, 45, 75, 75, 0, 0]
        })
        
        # Display portfolio table
        st.dataframe(portfolio_data, use_container_width=True)
    
    def render_performance_chart(self):
        """Render performance chart."""
        st.subheader("Performance Over Time")
        
        # Create sample performance data
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        equity_curve = 1000000 + np.cumsum(np.random.normal(1000, 2000, len(dates)))
        
        # Create figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=equity_curve,
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#1f77b4', width=2)
        ))
        
        fig.update_layout(
            title="Portfolio Equity Curve",
            xaxis_title="Date",
            yaxis_title="Portfolio Value (₹)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_risk_metrics(self):
        """Render risk metrics."""
        st.subheader("Risk Metrics")
        
        # Create risk metrics data
        risk_data = {
            'Metric': ['Portfolio Risk', 'Position Size', 'Daily Loss Limit', 
                      'Margin Utilization', 'VaR (95%)', 'Sharpe Ratio'],
            'Value': ['1.8%', '4.2%', '₹12,500/₹5,000', '65%', '₹25,000', '1.85'],
            'Status': ['✅', '✅', '⚠️', '✅', '✅', '✅']
        }
        
        risk_df = pd.DataFrame(risk_data)
        st.dataframe(risk_df, use_container_width=True)
        
        # Risk gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=1.8,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Portfolio Risk %"},
            gauge={
                'axis': {'range': [0, 5]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 1], 'color': "lightgreen"},
                    {'range': [1, 2], 'color': "yellow"},
                    {'range': [2, 5], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 2.0
                }
            }
        ))
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_trades_log(self):
        """Render trades log."""
        st.subheader("Recent Trades")
        
        # Create sample trades data
        trades_data = pd.DataFrame({
            'Timestamp': [
                '2024-01-15 10:30:25',
                '2024-01-15 11:15:42',
                '2024-01-15 13:45:18',
                '2024-01-15 14:20:33',
                '2024-01-15 15:10:05'
            ],
            'Symbol': [
                'NIFTY24JAN20000CE',
                'NIFTY24JAN19500PE',
                'NIFTY24JAN20000CE',
                'NIFTY24FEB19800CE',
                'NIFTY24FEB19200PE'
            ],
            'Action': ['SELL', 'SELL', 'BUY', 'SELL', 'SELL'],
            'Quantity': [50, 50, 50, 50, 50],
            'Price': [150.50, 120.25, 140.25, 180.75, 95.50],
            'Status': ['Filled', 'Filled', 'Filled', 'Filled', 'Filled']
        })
        
        st.dataframe(trades_data, use_container_width=True)
    
    def render_controls(self):
        """Render strategy controls."""
        st.subheader("Strategy Controls")
        
        # Strategy parameters
        with st.expander("Strategy Parameters", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                profit_target = st.slider("Profit Target (%)", 10, 100, 50)
                loss_limit = st.slider("Loss Limit (%)", 50, 200, 100)
                max_positions = st.number_input("Max Positions", 1, 20, 10)
            
            with col2:
                delta_range_low = st.slider("Delta Range Low", 0.05, 0.5, 0.15)
                delta_range_high = st.slider("Delta Range High", 0.1, 0.8, 0.25)
                min_oi = st.number_input("Min Open Interest", 100, 5000, 1000)
        
        # Control buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🟢 Start Strategy", use_container_width=True):
                st.success("Strategy started!")
        
        with col2:
            if st.button("⏸️ Pause Strategy", use_container_width=True):
                st.warning("Strategy paused!")
        
        with col3:
            if st.button("🔴 Stop Strategy", use_container_width=True):
                st.error("Strategy stopped!")
    
    def render_market_data(self):
        """Render market data."""
        st.subheader("Market Data")
        
        # Create sample market data
        market_data = pd.DataFrame({
            'Symbol': ['NIFTY', 'BANKNIFTY', 'SENSEX', 'NIFTY-I', 'BANKNIFTY-I'],
            'Last': [20150.25, 45200.75, 67850.50, 20175.00, 45250.25],
            'Change': [150.25, -75.50, 200.75, 175.00, -50.25],
            'Change %': [0.75, -0.17, 0.30, 0.87, -0.11],
            'Volume': ['1,250M', '850M', '350M', 'N/A', 'N/A']
        })
        
        st.dataframe(market_data, use_container_width=True)
    
    def run(self):
        """Run the dashboard application."""
        # Render header
        self.render_header()
        
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Overview", 
            "📈 Performance", 
            "⚠️ Risk", 
            "⚙️ Controls"
        ])
        
        with tab1:
            self.render_portfolio_overview()
            self.render_trades_log()
            self.render_market_data()
        
        with tab2:
            self.render_performance_chart()
            
            # Add performance metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Return", "12.5%", "+1.2%")
            
            with col2:
                st.metric("Annualized Return", "45.8%", "+3.5%")
            
            with col3:
                st.metric("Max Drawdown", "8.2%", "-0.5%")
            
            with col4:
                st.metric("Win Rate", "68.5%", "+2.1%")
        
        with tab3:
            self.render_risk_metrics()
            
            # Add risk analysis
            st.subheader("Risk Analysis")
            
            # Position distribution chart
            positions_by_type = pd.DataFrame({
                'Type': ['Short Calls', 'Short Puts', 'Long Stock'],
                'Count': [15, 12, 2]
            })
            
            fig = px.pie(positions_by_type, values='Count', names='Type',
                        title='Position Distribution')
            st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            self.render_controls()
            
            # Add configuration section
            with st.expander("Advanced Configuration"):
                st.subheader("API Settings")
                api_key = st.text_input("API Key", type="password")
                access_token = st.text_input("Access Token", type="password")
                
                st.subheader("Notification Settings")
                email_notifications = st.checkbox("Email Notifications")
                webhook_url = st.text_input("Webhook URL")
                
                if st.button("Save Configuration"):
                    st.success("Configuration saved!")


def main():
    """Main function to run the dashboard."""
    dashboard = StrategyDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()