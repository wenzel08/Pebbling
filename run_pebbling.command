#!/bin/bash
cd "$(dirname "$0")"
echo -ne "\033]0;Pebbling\007"
streamlit run Pebbling.py 