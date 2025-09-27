import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
import json
from typing import Dict, List
import logging

# Add the parent directory to the path to import from the project
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging_utils import get_logger
from config.config import OptionWheelConfig
from models.models import Position, Trade
from models.enums import OrderType, ProductType, TransactionType

logger = get_logger(__name__)

# Set up the Streamlit page
st.set_page_config(
    page_title="Options Wheel Strategy Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Options Wheel Strategy Dashboard")

class Dashboard:
    """
    Streamlit dashboard for monitoring the Options Wheel Strategy
    """
    
    def __init__(self):
        self.db_path = "trading_data.db"
        self.config = OptionWheelConfig()
    
    def get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def get_portfolio_overview(self) -> Dict:
        """Get portfolio overview data"""
        try:
            conn = self.get_db_connection()
            
            # Get positions
            positions_df = pd.read_sql_query("SELECT * FROM positions", conn)
            
            # Calculate portfolio metrics
            if not positions_df.empty:
                total_value = (positions_df['quantity'] * positions_df['last_price']).abs().sum()
                total_realized_pnl = positions_df['realized_pnl'].sum()
                total_unrealized_pnl = ((positions_df['last_price'] - positions_df['average_price']) * positions_df['quantity']).sum()
                total_pnl = total_realized_pnl + total_unrealized_pnl
                total_positions = len(positions_df)
                
                # Calculate today's P&L if trades exist
                today = datetime.now().date().isoformat()
                today_trades_df = pd.read_sql_query(
                    f"SELECT * FROM trades WHERE DATE(created_at) = '{today}'", conn
                )
                
                if not today_trades_df.empty:
                    today_pnl = today_trades_df['filled_quantity'] * (today_trades_df['average_price'] - today_trades_df['price'])
                    today_pnl = today_pnl.sum()
                else:
                    today_pnl = 0.0
            else:
                total_value = 0.0
                total_realized_pnl = 0.0
                total_unrealized_pnl = 0.0
                total_pnl = 0.0
                total_positions = 0
                today_pnl = 0.0
            
            conn.close()
            
            return {
                'total_value': total_value,
                'total_realized_pnl': total_realized_pnl,
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_pnl': total_pnl,
                'total_positions': total_positions,
                'today_pnl': today_pnl
            }
        except Exception as e:
            logger.error(f"Error getting portfolio overview: {str(e)}")
            return {
                'total_value': 0.0,
                'total_realized_pnl': 0.0,
                'total_unrealized_pnl': 0.0,
                'total_pnl': 0.0,
                'total_positions': 0,
                'today_pnl': 0.0
            }
    
    def get_positions_data(self) -> pd.DataFrame:
        """Get positions data for display"""
        try:
            conn = self.get_db_connection()
            df = pd.read_sql_query("SELECT * FROM positions ORDER BY updated_at DESC", conn)
            conn.close()
            
            # Calculate P&L columns if data exists
            if not df.empty:
                df['current_value'] = df['quantity'] * df['last_price']
                df['pnl'] = (df['last_price'] - df['average_price']) * df['quantity']
                df['pnl_percentage'] = ((df['last_price'] / df['average_price']) - 1) * 100
                df['position_type'] = df['quantity'].apply(lambda x: 'LONG' if x > 0 else ('SHORT' if x < 0 else 'FLAT'))
            
            return df
        except Exception as e:
            logger.error(f"Error getting positions data: {str(e)}")
            return pd.DataFrame()
    
    def get_trades_data(self, limit: int = 50) -> pd.DataFrame:
        """Get trades data for display"""
        try:
            conn = self.get_db_connection()
            query = f"SELECT * FROM trades ORDER BY created_at DESC LIMIT {limit}"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Convert timestamp to datetime if needed
            if not df.empty and 'order_timestamp' in df.columns:
                df['order_timestamp'] = pd.to_datetime(df['order_timestamp'])
            
            return df
        except Exception as e:
            logger.error(f"Error getting trades data: {str(e)}")
            return pd.DataFrame()
    
    def get_historical_trades_data(self) -> pd.DataFrame:
        """Get historical trades from all CSV files in the main directory and historical trades folder"""
        try:
            import os
            import glob
            
            # Define multiple search locations
            search_directories = [
                "/Users/nagashankar/pythonScripts/OWS",  # Main directory
                "/Users/nagashankar/pythonScripts/OWS/historical_trades"  # Historical trades directory
            ]
            
            # Look for all CSV files that match the tradebook pattern in all directories
            csv_files = []
            
            for directory in search_directories:
                if os.path.exists(directory):
                    # Look for tradebook files using multiple possible patterns
                    csv_patterns = [
                        os.path.join(directory, "tradebook-*.csv"),
                        os.path.join(directory, "*tradebook*.csv"),
                        os.path.join(directory, "*.csv")
                    ]
                    
                    for pattern in csv_patterns:
                        found_files = glob.glob(pattern)
                        # Filter to only include files that have trade-related content
                        for file in found_files:
                            filename = os.path.basename(file).lower()
                            # Include the file if it has 'tradebook' in the name or if it's in the historical trades directory
                            if 'tradebook' in filename or directory.endswith('historical_trades'):
                                csv_files.append(file)
            
            # Remove duplicates by converting to set and back to list
            csv_files = list(set(csv_files))
            
            if not csv_files:
                logger.warning("No tradebook CSV files found in the historical folder")
                return pd.DataFrame()
            
            # Process each CSV file and combine them
            all_dataframes = []
            
            for csv_path in csv_files:
                try:
                    df = pd.read_csv(csv_path)
                    
                    # Verify that required columns exist in this CSV
                    required_columns = ['symbol', 'trade_date', 'trade_type', 'quantity', 'price']
                    missing_cols = [col for col in required_columns if col not in df.columns]
                    
                    if missing_cols:
                        logger.warning(f"CSV file {csv_path} missing required columns: {missing_cols}. Skipping...")
                        continue
                    
                    # Process the historical trades data
                    if not df.empty:
                        # Convert trade_date to datetime
                        df['trade_date'] = pd.to_datetime(df['trade_date'])
                        # Convert order_execution_time to datetime if it exists
                        if 'order_execution_time' in df.columns:
                            df['order_execution_time'] = pd.to_datetime(df['order_execution_time'])
                        
                        # Add calculated columns for analysis
                        df['trade_type_clean'] = df['trade_type'].str.upper()
                        df['value'] = df['quantity'] * df['price']
                        
                        # Add source file information
                        df['source_file'] = os.path.basename(csv_path)
                        df['source_directory'] = os.path.basename(os.path.dirname(csv_path))
                        
                        # Map trade type to transaction type for consistency
                        df['transaction_type'] = df['trade_type'].str.upper()
                        
                        all_dataframes.append(df)
                    
                    logger.info(f"Loaded {len(df)} trades from {csv_path}")
                    
                except Exception as e:
                    logger.error(f"Error loading CSV file {csv_path}: {str(e)}")
                    continue
            
            if not all_dataframes:
                logger.warning("No valid CSV files were loaded")
                return pd.DataFrame()
            
            # Combine all dataframes
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            
            # Sort by trade date to have chronological order
            combined_df = combined_df.sort_values('trade_date').reset_index(drop=True)
            
            return combined_df
            
        except Exception as e:
            logger.error(f"Error getting historical trades data: {str(e)}")
            return pd.DataFrame()
    
    def get_filtered_historical_data(self, historical_df: pd.DataFrame, start_date=None, end_date=None, symbol_filter=None, year_filter=None, quarter_filter=None) -> pd.DataFrame:
        """Filter historical data based on various criteria"""
        filtered_df = historical_df.copy()
        
        if start_date:
            filtered_df = filtered_df[filtered_df['trade_date'] >= pd.to_datetime(start_date)]
        
        if end_date:
            filtered_df = filtered_df[filtered_df['trade_date'] <= pd.to_datetime(end_date)]
        
        if symbol_filter and symbol_filter != "All":
            filtered_df = filtered_df[filtered_df['symbol'] == symbol_filter]
        
        if year_filter and year_filter != "All":
            filtered_df = filtered_df[filtered_df['trade_date'].dt.year == int(year_filter)]
        
        if quarter_filter and quarter_filter != "All":
            quarter_num = int(quarter_filter.split('Q')[1])
            filtered_df = filtered_df[filtered_df['trade_date'].dt.quarter == quarter_num]
        
        return filtered_df

    def analyze_option_greeks_proxy(self, historical_df: pd.DataFrame) -> pd.DataFrame:
        """Create proxy analysis for option Greeks based on available trade data"""
        if historical_df.empty:
            return pd.DataFrame()
        
        df = historical_df.copy()
        
        # Ensure both date columns are datetime
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df['expiry_date'] = pd.to_datetime(df['expiry_date'])
        
        # Extract information from symbol name to infer Greeks-related characteristics
        # For Indian options, the format is typically: SYMBOL[DATE][STRIKE][CE/PE]
        # Example: NIFTY2140814950CE (NIFTY + 21APR08 + 14950 + CE)
        
        # Extract strike and option type from symbol (assuming format SYMBOL[YYMMDD]STRIKE[CE/PE])
        import re
        strikes = []
        option_types = []
        
        for symbol in df['symbol']:
            # Extract strike and option type from symbol
            # Pattern: Extract strike (consecutive digits) and CE/PE at the end
            match = re.search(r'(\d+)(CE|PE)$', symbol)
            if match:
                strike_part = match.group(1)
                type_part = match.group(2)
                
                strikes.append(int(strike_part))
                option_types.append(type_part)
            else:
                strikes.append(None)
                option_types.append(None)
        
        df['strike_price'] = strikes
        df['option_type'] = option_types
        
        # Calculate days to expiry (DTE) as a proxy for theta analysis using the original expiry_date
        df['dte'] = (df['expiry_date'] - df['trade_date']).dt.days
        
        # Calculate whether option is ITM, ATM, or OTM as a proxy for delta analysis
        # Note: We don't have underlying price, so we'll use a simplified approach
        # In a real system, you would need the underlying price at trade time
        df['is_call'] = df['option_type'] == 'CE'
        df['is_put'] = df['option_type'] == 'PE'
        
        # For now, we'll just identify some key Greeks-related characteristics
        # In a production system, you would calculate actual Greeks values
        df['is_itm'] = False  # Placeholder - would require underlying price
        df['is_otm'] = False  # Placeholder - would require underlying price
        
        return df

    def create_greeks_analysis_charts(self, historical_df: pd.DataFrame) -> tuple:
        """Create charts for option Greeks analysis"""
        analyzed_df = self.analyze_option_greeks_proxy(historical_df)
        
        if analyzed_df.empty or 'dte' not in analyzed_df.columns:
            # Return empty figures if analysis failed
            empty_fig = go.Figure()
            empty_fig.add_annotation(text="Insufficient data for Greeks analysis", 
                                   xref="paper", yref="paper",
                                   x=0.5, y=0.5, showarrow=False)
            return empty_fig, empty_fig, empty_fig
        
        # Filter out rows with invalid DTE
        valid_df = analyzed_df[analyzed_df['dte'].notna() & (analyzed_df['dte'] >= 0)]
        
        # Chart 1: Trades by Days to Expiry (Theta proxy)
        theta_fig = go.Figure()
        if not valid_df.empty:
            dte_counts = valid_df['dte'].value_counts().sort_index()
            theta_fig.add_trace(go.Scatter(
                x=dte_counts.index,
                y=dte_counts.values,
                mode='lines+markers',
                name='Trade Count by DTE',
                line=dict(color='red', width=2)
            ))
            
            theta_fig.update_layout(
                title="Trade Distribution by Days to Expiry (Theta Proxy)",
                xaxis_title="Days to Expiry",
                yaxis_title="Number of Trades",
                hovermode='x unified',
                template='plotly_white'
            )
        else:
            theta_fig.add_annotation(text="No valid DTE data", 
                                   xref="paper", yref="paper",
                                   x=0.5, y=0.5, showarrow=False)
        
        # Chart 2: Trades by Option Type (Delta proxy)
        delta_fig = go.Figure()
        if not valid_df.empty:
            option_counts = valid_df['option_type'].value_counts()
            delta_fig.add_trace(go.Pie(
                labels=option_counts.index,
                values=option_counts.values,
                name="Option Type Distribution"
            ))
            
            delta_fig.update_layout(
                title="Call vs Put Distribution (Delta Proxy)",
                template='plotly_white'
            )
        else:
            delta_fig.add_annotation(text="No valid option type data", 
                                   xref="paper", yref="paper",
                                   x=0.5, y=0.5, showarrow=False)
        
        # Chart 3: Trades by Strike Price (Gamma proxy)
        gamma_fig = go.Figure()
        if not valid_df.empty and valid_df['strike_price'].notna().any():
            # Group by strike price ranges for better visualization
            valid_strikes = valid_df[valid_df['strike_price'].notna()]
            strike_ranges = pd.cut(valid_strikes['strike_price'], bins=20)
            range_counts = strike_ranges.value_counts().sort_index()
            
            gamma_fig.add_trace(go.Bar(
                x=[str(interval) for interval in range_counts.index],
                y=range_counts.values,
                name='Strike Range Distribution',
                marker_color='orange'
            ))
            
            gamma_fig.update_layout(
                title="Trade Distribution by Strike Price Range (Gamma Proxy)",
                xaxis_title="Strike Price Range",
                yaxis_title="Number of Trades",
                template='plotly_white',
                xaxis_tickangle=-45
            )
        else:
            gamma_fig.add_annotation(text="No valid strike price data", 
                                   xref="paper", yref="paper",
                                   x=0.5, y=0.5, showarrow=False)
        
        return theta_fig, delta_fig, gamma_fig

    def create_year_over_year_chart(self, historical_df: pd.DataFrame) -> go.Figure:
        """Create year-over-year performance comparison chart"""
        if historical_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No historical trade data available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Extract year from trade_date
        df = historical_df.copy()
        df['year'] = df['trade_date'].dt.year
        
        # Group by year to calculate performance metrics
        yearly_performance = df.groupby('year').agg({
            'value': 'sum',
            'quantity': 'sum',
            'price': 'mean'
        }).reset_index()
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=yearly_performance['year'],
            y=yearly_performance['value'],
            name='Yearly Trade Value',
            marker_color='lightblue'
        ))
        
        fig.update_layout(
            title="Year-over-Year Trade Value",
            xaxis_title="Year",
            yaxis_title="Total Trade Value (₹)",
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig

    def create_quarter_over_quarter_chart(self, historical_df: pd.DataFrame) -> go.Figure:
        """Create quarter-over-quarter performance comparison chart"""
        if historical_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No historical trade data available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Extract year and quarter from trade_date
        df = historical_df.copy()
        df['year'] = df['trade_date'].dt.year
        df['quarter'] = df['trade_date'].dt.quarter
        df['year_quarter'] = df['year'].astype(str) + 'Q' + df['quarter'].astype(str)
        
        # Group by year-quarter to calculate performance metrics
        quarterly_performance = df.groupby(['year', 'quarter', 'year_quarter']).agg({
            'value': 'sum',
            'quantity': 'sum'
        }).reset_index()
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=quarterly_performance['year_quarter'],
            y=quarterly_performance['value'],
            name='Quarterly Trade Value',
            marker_color='lightgreen'
        ))
        
        fig.update_layout(
            title="Quarter-over-Quarter Trade Value",
            xaxis_title="Quarter",
            yaxis_title="Total Trade Value (₹)",
            hovermode='x unified',
            template='plotly_white',
            xaxis_tickangle=-45
        )
        
        return fig
    
    def create_equity_curve_chart(self, performance_df: pd.DataFrame) -> go.Figure:
        """Create equity curve chart"""
        if performance_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No performance data available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Filter for daily P&L or cumulative P&L metrics
        pnl_data = performance_df[
            performance_df['metric_name'].isin(['daily_pnl', 'cumulative_pnl', 'portfolio_value'])
        ]
        
        if pnl_data.empty:
            fig = go.Figure()
            fig.add_annotation(text="No P&L data available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            return fig
        
        fig = go.Figure()
        
        # Group by date and sum P&L for daily curve
        pnl_data['date'] = pd.to_datetime(pnl_data['timestamp']).dt.date
        daily_pnl = pnl_data.groupby('date')['value'].sum().reset_index()
        daily_pnl['cumulative'] = daily_pnl['value'].cumsum()
        
        fig.add_trace(go.Scatter(
            x=daily_pnl['date'], 
            y=daily_pnl['cumulative'],
            mode='lines+markers',
            name='Cumulative P&L',
            line=dict(color='blue', width=2)
        ))
        
        fig.update_layout(
            title="Equity Curve",
            xaxis_title="Date",
            yaxis_title="Cumulative P&L (₹)",
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    def create_pnl_by_symbol_chart(self, trades_df: pd.DataFrame) -> go.Figure:
        """Create P&L by symbol chart"""
        if trades_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No trade data available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            return fig
        
        # For now, just group by symbol and count trades
        # In a real system, we'd calculate actual P&L
        symbol_counts = trades_df['symbol'].value_counts().reset_index()
        symbol_counts.columns = ['symbol', 'trade_count']
        
        fig = px.bar(
            symbol_counts,
            x='symbol',
            y='trade_count',
            title="Number of Trades by Symbol"
        )
        
        fig.update_layout(
            xaxis_title="Symbol",
            yaxis_title="Number of Trades",
            template='plotly_white'
        )
        
        return fig

    def create_historical_pnl_chart(self, historical_df: pd.DataFrame) -> go.Figure:
        """Create P&L chart from historical trades"""
        if historical_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No historical trade data available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Group by trade_date and calculate daily P&L if possible
        # Since the CSV doesn't have explicit P&L, we'll aggregate trade values
        daily_summary = historical_df.groupby(historical_df['trade_date'].dt.date).agg({
            'value': 'sum',
            'quantity': 'sum'
        }).reset_index()
        
        fig = go.Figure()
        
        # Add the cumulative P&L line
        daily_summary['cumulative_value'] = daily_summary['value'].cumsum()
        
        fig.add_trace(go.Scatter(
            x=daily_summary['trade_date'],
            y=daily_summary['cumulative_value'],
            mode='lines+markers',
            name='Cumulative Trade Value',
            line=dict(color='green', width=2)
        ))
        
        fig.update_layout(
            title="Historical Trade Performance",
            xaxis_title="Date",
            yaxis_title="Cumulative Value (₹)",
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    def create_historical_trade_volume_chart(self, historical_df: pd.DataFrame) -> go.Figure:
        """Create trade volume chart from historical trades"""
        if historical_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No historical trade data available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Group by trade_date and calculate daily volume
        daily_volume = historical_df.groupby(historical_df['trade_date'].dt.date).agg({
            'value': 'sum',
            'quantity': 'sum'
        }).reset_index()
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=daily_volume['trade_date'],
            y=daily_volume['value'],
            name='Daily Trade Value',
            marker_color='lightblue'
        ))
        
        fig.update_layout(
            title="Daily Trade Volume",
            xaxis_title="Date",
            yaxis_title="Trade Value (₹)",
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    def create_historical_symbol_performance_chart(self, historical_df: pd.DataFrame) -> go.Figure:
        """Create chart showing performance by symbol"""
        if historical_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No historical trade data available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Group by symbol to get total value traded per symbol
        symbol_summary = historical_df.groupby('symbol').agg({
            'value': 'sum',
            'quantity': 'sum',
            'price': 'mean'
        }).reset_index()
        
        # Sort by value for better visualization
        symbol_summary = symbol_summary.sort_values('value', ascending=False)
        
        fig = px.bar(
            symbol_summary,
            x='symbol',
            y='value',
            title="Total Trade Value by Symbol",
            color='value',
            color_continuous_scale='viridis'
        )
        
        fig.update_layout(
            xaxis_title="Symbol",
            yaxis_title="Total Trade Value (₹)",
            template='plotly_white',
            xaxis_tickangle=-45
        )
        
        return fig
    
    def display_overview_tab(self):
        """Display the overview tab"""
        st.header("📈 Portfolio Overview")
        
        # Get portfolio data
        portfolio_data = self.get_portfolio_overview()
        
        # Display key metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        col1.metric("Portfolio Value", f"₹{portfolio_data['total_value']:,.2f}")
        col2.metric("Total P&L", f"₹{portfolio_data['total_pnl']:,.2f}", 
                    delta=f"₹{portfolio_data['today_pnl']:,.2f} today")
        col3.metric("Realized P&L", f"₹{portfolio_data['total_realized_pnl']:,.2f}")
        col4.metric("Unrealized P&L", f"₹{portfolio_data['total_unrealized_pnl']:,.2f}")
        col5.metric("Active Positions", portfolio_data['total_positions'])
        
        # Charts
        st.subheader("Performance Charts")
        
        # Get data
        performance_df = self.get_performance_data()
        trades_df = self.get_trades_data()
        positions_df = self.get_positions_data()
        
        # Create columns for charts
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("Equity Curve")
            equity_fig = self.create_equity_curve_chart(performance_df)
            st.plotly_chart(equity_fig, use_container_width=True)
        
        with chart_col2:
            st.subheader("P&L by Symbol")
            pnl_fig = self.create_pnl_by_symbol_chart(trades_df)
            st.plotly_chart(pnl_fig, use_container_width=True)
        
        # More charts below
        st.subheader("Position Analysis")
        pos_col1, pos_col2 = st.columns(2)
        
        with pos_col1:
            st.subheader("Position Distribution")
            pos_dist_fig = self.create_position_distribution_chart(positions_df)
            st.plotly_chart(pos_dist_fig, use_container_width=True)
        
        with pos_col2:
            st.subheader("Top Positions")
            if not positions_df.empty:
                # Show top 10 positions by absolute value
                positions_df['abs_value'] = (positions_df['quantity'] * positions_df['last_price']).abs()
                top_positions = positions_df.nlargest(10, 'abs_value')[
                    ['symbol', 'quantity', 'average_price', 'last_price', 'pnl']
                ]
                st.dataframe(top_positions)
            else:
                st.write("No positions available")

    def get_performance_data(self) -> pd.DataFrame:
        """Get performance metrics data"""
        try:
            conn = self.get_db_connection()
            df = pd.read_sql_query("SELECT * FROM performance_metrics ORDER BY timestamp ASC", conn)
            conn.close()
            
            # Convert timestamp to datetime
            if not df.empty and 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
        except Exception as e:
            logger.error(f"Error getting performance data: {str(e)}")
            return pd.DataFrame()

    def create_position_distribution_chart(self, positions_df: pd.DataFrame) -> go.Figure:
        """Create position distribution chart"""
        if positions_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No position data available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            return fig
        
        fig = px.pie(
            positions_df, 
            values=positions_df['quantity'].abs(), 
            names='symbol',
            title="Position Distribution by Quantity"
        )
        
        return fig
    
    def display_positions_tab(self):
        """Display the positions tab"""
        st.header("💼 Current Positions")
        
        positions_df = self.get_positions_data()
        
        if positions_df.empty:
            st.info("No positions available")
            return
        
        # Add calculated columns if they don't exist
        if 'pnl' not in positions_df.columns:
            positions_df['current_value'] = positions_df['quantity'] * positions_df['last_price']
            positions_df['pnl'] = (positions_df['last_price'] - positions_df['average_price']) * positions_df['quantity']
            positions_df['pnl_percentage'] = ((positions_df['last_price'] / positions_df['average_price']) - 1) * 100
            positions_df['position_type'] = positions_df['quantity'].apply(lambda x: 'LONG' if x > 0 else ('SHORT' if x < 0 else 'FLAT'))
        
        # Display positions
        st.dataframe(
            positions_df[[
                'symbol', 'quantity', 'average_price', 'last_price', 
                'pnl', 'pnl_percentage', 'position_type'
            ]].style.format({
                'average_price': '₹{:.2f}',
                'last_price': '₹{:.2f}',
                'pnl': '₹{:.2f}',
                'pnl_percentage': '{:.2f}%'
            }),
            use_container_width=True
        )
    
    def display_trades_tab(self):
        """Display the trades tab"""
        st.header("🛒 Recent Trades")
        
        trades_df = self.get_trades_data(limit=100)
        
        if trades_df.empty:
            st.info("No trades available")
            return
        
        # Display trades
        st.dataframe(
            trades_df[[
                'order_id', 'symbol', 'transaction_type', 'quantity', 
                'price', 'average_price', 'filled_quantity', 'status', 'created_at'
            ]].style.format({
                'price': '₹{:.2f}',
                'average_price': '₹{:.2f}'
            }),
            use_container_width=True
        )
    
    def display_historical_trades_tab(self):
        """Display the historical trades tab"""
        st.header("📈 Historical Trade Analysis")
        
        # Load historical trades
        historical_df = self.get_historical_trades_data()
        
        if historical_df.empty:
            st.info("No historical trade data available. Please ensure tradebook CSV files exist in the historical trades folder.")
            return
        
        # Get unique source files that were loaded
        if 'source_file' in historical_df.columns:
            unique_files = historical_df['source_file'].unique()
            st.sidebar.subheader("Loaded Files")
            for file in unique_files:
                st.sidebar.write(f"• {file}")
        
        # Filters section
        st.sidebar.subheader("Filters")
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(historical_df['trade_date'].min().date(), historical_df['trade_date'].max().date()),
            key="date_range"
        )
        
        # Get unique years for year filter
        unique_years = ['All'] + sorted(historical_df['trade_date'].dt.year.astype(str).unique().tolist())
        selected_year = st.sidebar.selectbox("Year", unique_years, key="year_filter")
        
        # Get unique quarters for quarter filter
        historical_df['quarter'] = historical_df['trade_date'].dt.to_period('Q')
        unique_quarters = ['All'] + sorted(historical_df['quarter'].astype(str).unique().tolist())
        selected_quarter = st.sidebar.selectbox("Quarter", unique_quarters, key="quarter_filter")
        
        # Get unique symbols for symbol filter
        unique_symbols = ['All'] + sorted(historical_df['symbol'].unique().tolist())
        selected_symbol = st.sidebar.selectbox("Symbol", unique_symbols, key="symbol_filter")
        
        # Apply filters
        filtered_df = self.get_filtered_historical_data(
            historical_df,
            start_date=date_range[0] if len(date_range) > 0 else None,
            end_date=date_range[1] if len(date_range) > 1 else date_range[0] if len(date_range) > 0 else None,
            symbol_filter=selected_symbol if selected_symbol != 'All' else None,
            year_filter=selected_year if selected_year != 'All' else None,
            quarter_filter=selected_quarter if selected_quarter != 'All' else None
        )
        
        st.subheader(f"Historical Trades Overview ({len(filtered_df)} trades found)")
        
        # Display summary statistics
        total_trades = len(filtered_df)
        total_value = filtered_df['value'].sum()
        unique_symbols = filtered_df['symbol'].nunique()
        date_range_str = f"{filtered_df['trade_date'].min().strftime('%Y-%m-%d')} to {filtered_df['trade_date'].max().strftime('%Y-%m-%d')}"
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Trades", total_trades)
        col2.metric("Total Value", f"₹{total_value:,.2f}")
        col3.metric("Unique Symbols", unique_symbols)
        col4.metric("Date Range", date_range_str)
        
        # Charts for historical trades
        st.subheader("Historical Performance Charts")
        
        # Create columns for charts
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("Cumulative Trade Performance")
            pnl_fig = self.create_historical_pnl_chart(filtered_df)
            st.plotly_chart(pnl_fig, use_container_width=True)
        
        with chart_col2:
            st.subheader("Daily Trade Volume")
            volume_fig = self.create_historical_trade_volume_chart(filtered_df)
            st.plotly_chart(volume_fig, use_container_width=True)
        
        # Year-over-year and Quarter-over-quarter charts
        chart_col3, chart_col4 = st.columns(2)
        
        with chart_col3:
            st.subheader("Year-over-Year Performance")
            yoy_fig = self.create_year_over_year_chart(historical_df)
            st.plotly_chart(yoy_fig, use_container_width=True)
        
        with chart_col4:
            st.subheader("Quarter-over-Quarter Performance")
            qoq_fig = self.create_quarter_over_quarter_chart(historical_df)
            st.plotly_chart(qoq_fig, use_container_width=True)
        
        # Greeks Analysis section
        st.subheader("Option Greeks Analysis (Proxy)")
        theta_fig, delta_fig, gamma_fig = self.create_greeks_analysis_charts(filtered_df)
        
        greeks_col1, greeks_col2 = st.columns(2)
        
        with greeks_col1:
            st.plotly_chart(theta_fig, use_container_width=True)  # Theta analysis (DTE)
            st.plotly_chart(gamma_fig, use_container_width=True)  # Gamma analysis (Strike)
        
        with greeks_col2:
            st.plotly_chart(delta_fig, use_container_width=True)  # Delta analysis (Call/Put)
        
        # Add explanation of Greeks analysis
        with st.expander("Understanding the Greeks Analysis"):
            st.write("""
            **Theta Analysis (Days to Expiry)**: Shows how trades are distributed across different time to expiry. 
            Options with fewer days to expiry typically have higher theta (time decay).
            
            **Delta Analysis (Call vs Put)**: Shows the distribution of call vs put options traded. 
            Delta measures the sensitivity of option price to changes in the underlying asset price.
            
            **Gamma Analysis (Strike Price)**: Shows the distribution of trades across strike price ranges. 
            Gamma measures the rate of change in delta for movements in the underlying asset.
            """)
        
        # Additional chart below
        st.subheader("Symbol Performance")
        symbol_fig = self.create_historical_symbol_performance_chart(filtered_df)
        st.plotly_chart(symbol_fig, use_container_width=True)
        
        # Display historical trades dataframe with filters applied
        st.subheader("Historical Trades Data")
        st.dataframe(
            filtered_df[[
                'source_directory', 'source_file', 'symbol', 'trade_type', 'quantity', 'price', 
                'trade_date', 'expiry_date', 'value'
            ]].style.format({
                'price': '₹{:.2f}',
                'value': '₹{:.2f}'
            }),
            use_container_width=True
        )
    
    def display_performance_tab(self):
        """Display the performance tab"""
        st.header("🏆 Performance Metrics")
        
        performance_df = self.get_performance_data()
        
        if performance_df.empty:
            st.info("No performance metrics available")
            return
        
        # Display performance data
        st.subheader("All Performance Metrics")
        st.dataframe(performance_df)
        
        # Calculate some key metrics
        st.subheader("Key Performance Indicators")
        
        if not performance_df.empty:
            # Calculate win rate, average P&L, etc. (simplified)
            daily_pnl = performance_df[performance_df['metric_name'] == 'daily_pnl']
            
            if not daily_pnl.empty:
                wins = len(daily_pnl[daily_pnl['value'] > 0])
                losses = len(daily_pnl[daily_pnl['value'] < 0])
                total_trades = len(daily_pnl)
                
                win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
                
                avg_win = daily_pnl[daily_pnl['value'] > 0]['value'].mean() if wins > 0 else 0
                avg_loss = daily_pnl[daily_pnl['value'] < 0]['value'].mean() if losses > 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Win Rate", f"{win_rate:.2f}%")
                col2.metric("Total Days", total_trades)
                col3.metric("Average Win", f"₹{avg_win:,.2f}")
                col4.metric("Average Loss", f"₹{avg_loss:,.2f}")
    
    def display_risk_tab(self):
        """Display the risk tab"""
        st.header("⚠️ Risk Management")
        
        # Use placeholder risk metrics since we don't have a live risk manager connection
        st.subheader("Risk Limits")
        
        # Display config-specified risk limits
        col1, col2, col3 = st.columns(3)
        col1.metric("Max Daily Loss", f"₹{self.config.max_daily_loss_limit:,.2f}")
        col2.metric("Max Concurrent Positions", self.config.max_concurrent_positions)
        col3.metric("Max Portfolio Risk", f"{self.config.max_portfolio_risk:.2%}")
        
        st.subheader("Risk Metrics")
        
        # Get position data
        positions_df = self.get_positions_data()
        portfolio_data = self.get_portfolio_overview()
        
        if not positions_df.empty and portfolio_data['total_value'] > 0:
            # Calculate risk metrics
            total_position_value = (positions_df['quantity'] * positions_df['last_price']).abs().sum()
            portfolio_risk_percentage = (total_position_value / portfolio_data['total_value']) * 100
            current_positions_count = len(positions_df)
            
            # Check for risk limit breaches
            daily_loss_exceeded = abs(portfolio_data['daily_loss']) >= self.config.max_daily_loss_limit
            position_limit_exceeded = current_positions_count >= self.config.max_concurrent_positions
            portfolio_risk_exceeded = portfolio_risk_percentage >= self.config.max_portfolio_risk
            
            # Display the metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Portfolio Risk", f"{portfolio_risk_percentage:.2f}%", 
                       f"{self.config.max_portfolio_risk:.2%} limit")
            col2.metric("Active Positions", current_positions_count, 
                       f"{self.config.max_concurrent_positions} limit")
            col3.metric("Daily Loss", f"₹{portfolio_data['daily_loss']:,.2f}", 
                       f"₹{self.config.max_daily_loss_limit:,.2f} limit")
            
            # Display alerts for risk breaches
            if daily_loss_exceeded:
                st.warning(f"⚠️ Daily loss limit exceeded: ₹{portfolio_data['daily_loss']:,.2f} >= ₹{self.config.max_daily_loss_limit:,.2f}")
            
            if position_limit_exceeded:
                st.warning(f"⚠️ Position limit exceeded: {current_positions_count} >= {self.config.max_concurrent_positions}")
            
            if portfolio_risk_exceeded:
                st.warning(f"⚠️ Portfolio risk limit exceeded: {portfolio_risk_percentage:.2f}% >= {self.config.max_portfolio_risk:.2f}%")
        else:
            st.info("No position data available for risk analysis")
        
        # Add system health check
        st.subheader("System Health")
        with st.expander("Health Status"):
            # Check various health indicators
            is_running = True  # This would come from actual strategy status
            has_positions = len(positions_df) > 0
            db_connection_ok = self._test_db_connection()
            has_recent_activity = portfolio_data['today_pnl'] != 0 or len(positions_df) > 0
            
            # Display health indicators
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                status_color = "🟢" if is_running else "🔴"
                st.write(f"**Strategy Status**: {status_color}")
                
            with col2:
                status_color = "🟢" if db_connection_ok else "🔴"
                st.write(f"**DB Connection**: {status_color}")
                
            with col3:
                status_color = "🟢" if has_positions else "🟡"
                st.write(f"**Active Positions**: {status_color}")
                
            with col4:
                status_color = "🟢" if has_recent_activity else "🟡"
                st.write(f"**Recent Activity**: {status_color}")
        
        # Add risk controls
        st.subheader("Risk Controls")
        with st.expander("Risk Management Settings"):
            st.write("Risk settings as configured in the strategy")
            # Display current configuration (excluding sensitive data)
            risk_settings = {
                'Max Daily Loss Limit': f"₹{self.config.max_daily_loss_limit:,.2f}",
                'Max Concurrent Positions': self.config.max_concurrent_positions,
                'Max Portfolio Risk': f"{self.config.max_portfolio_risk:.2%}",
                'Min Open Interest': self.config.min_open_interest,
                'OTM Delta Range': f"{self.config.otm_delta_range_low:.2f} - {self.config.otm_delta_range_high:.2f}",
                'Profit Target': f"{self.config.profit_target_percentage:.2%}",
                'Stop Loss': f"{self.config.loss_limit_percentage:.2%}"
            }
            
            for key, value in risk_settings.items():
                st.write(f"**{key}**: {value}")
    
    def _test_db_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False
    
    def display_controls_tab(self):
        """Display the controls tab"""
        st.header("🎛️ Strategy Controls")
        
        st.subheader("Strategy Status")
        
        # Show strategy status (placeholder)
        status = st.selectbox("Strategy Status", ["Running", "Paused", "Stopped"])
        st.write(f"Current status: **{status}**")
        
        # Add control buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Start Strategy", type="primary"):
                st.success("Strategy started!")
        
        with col2:
            if st.button("Pause Strategy", type="secondary"):
                st.warning("Strategy paused!")
        
        with col3:
            if st.button("Stop Strategy", type="secondary"):
                st.error("Strategy stopped!")
        
        st.subheader("Configuration")
        
        # Allow modifying key parameters
        col1, col2 = st.columns(2)
        
        with col1:
            new_symbol = st.text_input("Symbol", value=self.config.symbol)
            new_quantity = st.number_input("Quantity per Lot", value=self.config.quantity_per_lot, min_value=1)
            new_profit_target = st.number_input(
                "Profit Target Percentage", 
                value=self.config.profit_target_percentage,
                min_value=0.01,
                max_value=1.0,
                format="%.3f"
            )
        
        with col2:
            new_stop_loss = st.number_input(
                "Stop Loss Percentage",
                value=self.config.loss_limit_percentage,
                min_value=0.01,
                max_value=1.0,
                format="%.3f"
            )
            new_max_positions = st.number_input(
                "Max Concurrent Positions", 
                value=self.config.max_concurrent_positions,
                min_value=1
            )
            new_daily_loss_limit = st.number_input(
                "Max Daily Loss Limit (₹)", 
                value=self.config.max_daily_loss_limit,
                min_value=0.0
            )
        
        if st.button("Update Configuration"):
            # In a real implementation, this would update the strategy configuration
            st.success("Configuration updated!")
        
        st.subheader("System Actions")
        
        # Add system action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Reset Daily Metrics"):
                st.info("Daily metrics reset!")
        with col2:
            if st.button("Force Position Close"):
                st.warning("Position close action would be executed!")
        
        with col3:
            if st.button("Export Data"):
                st.info("Data export initiated!")

# Run the dashboard
if __name__ == "__main__":
    dashboard = Dashboard()
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Overview", 
        "💼 Positions", 
        "🛒 Trades", 
        "📊 Historical Trades",
        "🏆 Performance", 
        "⚠️ Risk", 
        "🎛️ Controls"
    ])
    
    with tab1:
        dashboard.display_overview_tab()
    
    with tab2:
        dashboard.display_positions_tab()
    
    with tab3:
        dashboard.display_trades_tab()
    
    with tab4:
        dashboard.display_historical_trades_tab()
    
    with tab5:
        dashboard.display_performance_tab()
    
    with tab6:
        dashboard.display_risk_tab()
    
    with tab7:
        dashboard.display_controls_tab()
    
    # Add last updated info
    st.sidebar.markdown("---")
    st.sidebar.info(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.sidebar.info(f"Connected to: {dashboard.db_path}")