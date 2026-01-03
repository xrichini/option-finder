# ai_dashboard_integration.py
"""
Example showing how to integrate AI-enhanced analysis into the existing dashboard
This demonstrates the key changes needed to upgrade your current dashboard.
"""

import sys
import os

# Add the project root to the sys.path to resolve module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from data.enhanced_screener import EnhancedOptionsScreener
from utils.config import Config
from utils.async_utils import run_async_in_streamlit

# Example of how to modify the existing dashboard methods

def render_ai_controls():
    """Render AI-specific controls in the sidebar"""
    if Config.has_ai_capabilities():
        st.sidebar.markdown("### 🧠 AI Analysis")
        
        ai_enabled = st.sidebar.checkbox(
            "Enable AI Analysis",
            value=st.session_state.get('ai_enabled', True),
            help="Enable AI-powered fundamental and sentiment analysis for top options"
        )
        st.session_state.ai_enabled = ai_enabled
        
        if ai_enabled:
            ai_top_n = st.sidebar.slider(
                "AI Analysis Count",
                min_value=1,
                max_value=10,
                value=st.session_state.get('ai_top_n', 5),
                help="Number of top results to enhance with AI analysis"
            )
            st.session_state.ai_top_n = ai_top_n
            
            # Show AI capabilities status
            with st.sidebar.expander("🔧 AI Status"):
                openai_status = "✅" if Config.get_openai_api_key() else "❌"
                perplexity_status = "✅" if Config.get_perplexity_api_key() else "❌"
                
                st.write(f"OpenAI API: {openai_status}")
                st.write(f"Perplexity API: {perplexity_status}")
                
                if not Config.get_openai_api_key():
                    st.warning("Set OPENAI_API_KEY for fundamental analysis")
                if not Config.get_perplexity_api_key():
                    st.warning("Set PERPLEXITY_API_KEY for news/sentiment analysis")
    else:
        st.sidebar.info("💡 Configure AI API keys to enable enhanced analysis")

async def run_enhanced_screening(symbols, option_type):
    """Enhanced screening function with AI analysis"""
    
    # Initialize enhanced screener
    screener = EnhancedOptionsScreener(
        enable_ai=st.session_state.get('ai_enabled', False)
    )
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(progress, message):
        progress_bar.progress(progress)
        status_text.text(message)
    
    try:
        # Run enhanced screening with AI
        results = await screener.screen_with_ai_analysis(
            symbols=symbols,
            option_type=option_type,
            max_dte=st.session_state.get('max_dte', 7),
            min_volume=st.session_state.get('min_volume', 1000),
            min_oi=st.session_state.get('min_oi', 500),
            min_whale_score=st.session_state.get('min_whale_score', 70),
            enable_ai_for_top_n=st.session_state.get('ai_top_n', 5),
            progress_callback=update_progress
        )
        
        # Generate portfolio strategy if AI is enabled
        portfolio_strategy = None
        if st.session_state.get('ai_enabled', False) and results:
            status_text.text("Generating AI portfolio strategy...")
            portfolio_strategy = await screener.generate_portfolio_strategy(results)
        
        progress_bar.empty()
        status_text.empty()
        
        return results, portfolio_strategy
        
    except Exception as e:
        st.error(f"Error in enhanced screening: {e}")
        return [], None
    finally:
        await screener.close()

def display_ai_enhanced_results(results, portfolio_strategy=None):
    """Display results with AI enhancements"""
    
    if not results:
        st.warning("No results found matching the criteria.")
        return
    
    # Display portfolio strategy if available
    if portfolio_strategy:
        render_portfolio_strategy(portfolio_strategy)
    
    # Enhanced results table with AI columns
    st.subheader(f"📊 Results ({len(results)} options found)")
    
    # Prepare data for display
    display_data = []
    for result in results:
        row = {
            'Symbol': result.symbol,
            'Option': result.option_symbol,
            'Strike': f"${result.strike}",
            'DTE': result.dte,
            'Side': result.side.upper(),
            'Volume': f"{result.volume_1d:,}",
            'OI': f"{result.open_interest:,}",
            'Vol/OI': f"{result.vol_oi_ratio:.2f}",
            'Whale Score': f"{result.whale_score:.0f}",
            'Block Size': result.block_size_category,
            'Historical': result.volume_vs_average_display,
            'AI Analysis': result.ai_summary_display,
            'AI Badge': result.ai_badge,
            'Anomaly': result.anomaly_badge
        }
        display_data.append(row)
    
    # Display enhanced table
    df = st.dataframe(
        display_data,
        use_container_width=True,
        column_config={
            'Whale Score': st.column_config.ProgressColumn(
                'Whale Score',
                min_value=0,
                max_value=100,
                format="%.0f"
            )
        }
    )
    
    # AI Analysis Details for top results
    if any(result.ai_badge for result in results[:5]):
        render_detailed_ai_analysis(results[:5])

def render_portfolio_strategy(strategy):
    """Render AI-generated portfolio strategy"""
    st.subheader("🧠 AI Portfolio Strategy")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write(f"**Strategy:** {strategy['strategy_summary']}")
        
        if strategy['recommendations']:
            st.write("**Recommendations:**")
            for rec in strategy['recommendations']:
                st.write(f"• {rec}")
    
    with col2:
        confidence = strategy['confidence']
        st.metric("Confidence", f"{confidence}%", delta=None)
        
        if confidence > 80:
            st.success("High Confidence")
        elif confidence > 60:
            st.warning("Medium Confidence")
        else:
            st.error("Low Confidence")
    
    # Risk factors
    if strategy['risk_factors']:
        with st.expander("⚠️ Risk Factors"):
            for risk in strategy['risk_factors']:
                st.write(f"• {risk}")
    
    # Detailed analysis
    if strategy.get('detailed_analysis'):
        with st.expander("📈 Detailed Analysis"):
            st.json(strategy['detailed_analysis'])

def render_detailed_ai_analysis(top_results):
    """Render detailed AI analysis for top results"""
    st.subheader("🤖 AI Analysis Details")
    
    for result in top_results:
        if not hasattr(result, '_ai_analysis') or not result._ai_analysis:
            continue
        
        with st.expander(f"📊 {result.symbol} - {result.option_symbol}"):
            ai_analysis = result._ai_analysis
            
            # Create tabs for different analysis types
            tabs = st.tabs(["Fundamental", "Sentiment", "Catalysts"])
            
            # Fundamental Analysis
            with tabs[0]:
                if 'fundamental' in ai_analysis:
                    fund_analysis = ai_analysis['fundamental']
                    st.write(f"**Summary:** {fund_analysis.summary}")
                    st.write(f"**Confidence:** {fund_analysis.confidence_score}%")
                    
                    if fund_analysis.recommendations:
                        st.write("**Recommendations:**")
                        for rec in fund_analysis.recommendations:
                            st.write(f"• {rec}")
                    
                    if fund_analysis.detailed_analysis:
                        st.json(fund_analysis.detailed_analysis)
                else:
                    st.info("Fundamental analysis not available")
            
            # Sentiment Analysis
            with tabs[1]:
                if 'sentiment' in ai_analysis:
                    sentiment = ai_analysis['sentiment']
                    sentiment_score = sentiment.detailed_analysis.get('sentiment_score', 50)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Sentiment Score", f"{sentiment_score}/100")
                    with col2:
                        if sentiment_score > 60:
                            st.success("Bullish")
                        elif sentiment_score < 40:
                            st.error("Bearish")
                        else:
                            st.warning("Neutral")
                    
                    st.write(f"**Analysis:** {sentiment.summary}")
                else:
                    st.info("Sentiment analysis not available")
            
            # Catalysts
            with tabs[2]:
                if 'catalysts' in ai_analysis:
                    catalysts = ai_analysis['catalysts']
                    catalyst_data = catalysts.detailed_analysis.get('catalysts', [])
                    
                    if catalyst_data:
                        for catalyst in catalyst_data:
                            sentiment_emoji = "🟢" if catalyst['impact_sentiment'] == 'bullish' else "🔴" if catalyst['impact_sentiment'] == 'bearish' else "🟡"
                            st.write(f"{sentiment_emoji} **{catalyst['event_type'].title()}:** {catalyst['description']}")
                    else:
                        st.info("No recent catalysts found")
                else:
                    st.info("Catalyst analysis not available")

# Example of how to modify the main dashboard run method
def enhanced_dashboard_main():
    """Modified main dashboard method with AI integration"""
    
    # Existing header and controls...
    st.title("🐋 AI-Enhanced Options Whale Screener")
    
    # Add AI controls to sidebar
    render_ai_controls()
    
    # Main scanning interface
    if st.button("🔍 Run Enhanced Scan", type="primary"):
        if not st.session_state.get('optionable_symbols'):
            st.error("No symbols loaded. Please load symbols first.")
            return
        
        # Run enhanced screening with AI
        results, strategy = run_async_in_streamlit(
            run_enhanced_screening(
                symbols=st.session_state.optionable_symbols[:50],  # Limit for demo
                option_type='call'  # or get from user selection
            )
        )
        
        # Store results in session state
        st.session_state.last_results = results
        st.session_state.last_strategy = strategy
    
    # Display results if available
    if st.session_state.get('last_results'):
        display_ai_enhanced_results(
            st.session_state.last_results,
            st.session_state.get('last_strategy')
        )

if __name__ == "__main__":
    enhanced_dashboard_main()