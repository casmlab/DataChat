#!/usr/bin/env python
# coding: utf-8

# Reference: https://github.com/tomasonjo/NeoGPT-Explorer/tree/main/streamlit/src

### driver
from neo4j import GraphDatabase

host = 'bolt://localhost:7687'
user = 'neo4j'
password = "ICPSRCHATEXP"
driver = GraphDatabase.driver(host, auth=(user, password))


def read_query(query, params={}):
    with driver.session() as session:
        result = session.run(query, params)
        response = [r.values()[0] for r in result]
        return response


# def get_article_text(title):
#     text = read_query(
#         "MATCH (a:Article {webTitle:$title}) RETURN a.bodyContent as response", {'title': title})
#     return text


### train cypher

# schema = """

# """

examples = """
# What are the latest datasets?
MATCH (a:Dataset) RETURN a.name a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the most cited datasets?
MATCH (a:Dataset) RETURN a.name + " " + a.url AS response ORDER BY a.dataRefCount DESC LIMIT 3
# What are the most used datasets?
MATCH (a:Dataset) RETURN a.name + " " +  a.url AS response ORDER BY a.dataUserCount DESC LIMIT 3
# What are the latest datasets not owned by ICPSR?
MATCH (a:Dataset) WHERE a.owner <> 'ICPSR' RETURN a.name + " " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets about alcohol?
MATCH (a:Dataset) WHERE a.name CONTAINS 'alcohol' RETURN a.name + " " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets that mention alcohol?
MATCH (a:Dataset)-[:HAS_TERM]->(t:Term) WHERE t.name CONTAINS 'alcohol' RETURN a.name + " " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets in the United States Historical Election Returns Series?
MATCH (a:Dataset)-[:HAS_SERIES]->(s:Series) WHERE s.name = 'United States Historical Election Returns Series' RETURN a.name + " " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets onwed by ICPSR?
MATCH (a:Dataset)-[:HAS_OWNER]->(o:Owner) WHERE o.name = 'ICPSR' RETURN a.name + " " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets funder by National Science Foundation?
MATCH (a:Dataset)-[:HAS_FUNDER]->(f:Funder) WHERE f.name = "National Science Foundation" RETURN a.name + " " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets funder by government?
MATCH (a:Dataset)-[:HAS_FUNDER]->(f:Funder) WHERE f.type = "government" RETURN a.name + " " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets that include data from United States?
MATCH (a:Dataset)-[:HAS_LOCATION]->(l:Location) WHERE (l.name = "United States" OR l.name = "U.S.") RETURN a.name + " " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets that include country level data?
MATCH (a:Dataset)-[:HAS_LOCATION]->(l:Location) WHERE l.type = "country" RETURN a.name + " " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the most cited publications of datasets about alcohol?
MATCH (a:Dataset)-[:CITED_BY]->(p:Publication) WHERE a.name CONTAINS 'alcohol' RETURN p.name AS response ORDER BY p.pubRefCount DESC LIMIT 3
"""

# examples_eg = """
# # What are the latest datasets?
# MATCH (a:Dataset) RETURN a.name AS response ORDER BY a.date DESC LIMIT 3
# # What are the most cited datasets?
# MATCH (a:Dataset) RETURN a.name AS response ORDER BY a.dataRefCount DESC LIMIT 3
# # What are the most used datasets?
# MATCH (a:Dataset) RETURN a.name AS response ORDER BY a.dataUserCount DESC LIMIT 3
# # What are the latest datasets not owned by ICPSR?
# MATCH (a:Dataset) WHERE a.owner <> 'ICPSR' RETURN a.name AS response ORDER BY a.date DESC LIMIT 3
# """

import os
import openai
import streamlit as st
from streamlit_chat import message

openai.api_key = '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'

### eg
# prompt_eg = "What are the earlest datasets?"
# prompt_input=examples_eg + "\n#" + prompt_eg
# completions = openai.ChatCompletion.create(
#     model="gpt-3.5-turbo",
#     max_tokens=1000,
#     n=1,
#     stop=None,
#     temperature=0.5,
#     messages=[{"role": "user", "content": prompt_input}]
# )
# cypher_query = completions['choices'][0]['message']['content']
# message = read_query(cypher_query)
# print(message)
# print(cypher_query)


st.title("DataChat: Chat with ICPSR Datasets")

# need to test here first
def generate_response(prompt, cypher=True):
    #prompt_eg = "What are the earlest datasets?"
    prompt_input=examples + "\n#" + prompt
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.5,
        messages=[{"role": "user", "content": prompt_input}]
    )
    cypher_query = completions['choices'][0]['message']['content']
    message = read_query(cypher_query)
    return message, cypher_query

# Storing the chat
if 'generated' not in st.session_state:
    st.session_state['generated'] = []

if 'past' not in st.session_state:
    st.session_state['past'] = []


def get_text():
    input_text = st.text_input(
        "Feel free to ask a question about ICPSR datasets", "", key="input")
    return input_text


col1, col2 = st.columns([2, 1])


with col2:
    another_placeholder = st.empty()
with col1:
    placeholder = st.empty()
user_input = get_text()


if user_input:
    output, cypher_query = generate_response(user_input)
    # store the output
    st.session_state.past.append(user_input)
    st.session_state.generated.append((output, cypher_query))

# Message placeholder
with placeholder.container():
    if st.session_state['generated']:
        message(st.session_state['past'][-1],
                is_user=True, key=str(-1) + '_user')
        for j, text in enumerate(st.session_state['generated'][-1][0]):
            message(text, key=str(-1) + str(j))

# Generated Cypher statements
with another_placeholder.container():
    if st.session_state['generated']:
        st.text_area("Generated Cypher statement",
                     st.session_state['generated'][-1][1], height=240)

