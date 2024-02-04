import pathlib
import textwrap
import os
import google.generativeai as genai
from IPython.display import display
from IPython.display import Markdown
import streamlit as st

'''def to_markdown(text):
  text = text.replace('•', '  *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))'''

def gemini(text):
  GOOGLE_API_KEY=st.secrets["GOOGLE_API_KEY"]
  genai.configure(api_key=GOOGLE_API_KEY)

  model = genai.GenerativeModel('gemini-pro')
  chat = model.start_chat(history=[])

  response = chat.send_message('%s -- Please answer as concisely as you can, avoiding any extra conversation or text. DO NOT USE <b> tag for bold, please use ** instead' % text)
  gemini_response = response.text

  return gemini_response

