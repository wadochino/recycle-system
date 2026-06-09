import streamlit as st
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("テストページ")

# グラフテスト
fig = go.Figure(data=[
    go.Bar(x=['A', 'B', 'C'], y=[1, 2, 3])
])
st.plotly_chart(fig)

st.write("✅ Plotly は正常に動作しています")
