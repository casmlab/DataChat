#!/usr/bin/env python
# coding: utf-8

# Reference: https://github.com/tomasonjo/NeoGPT-Explorer/tree/main/streamlit/src
# Reference: https://github.com/ChrisDelClea/streamlit-agraph

### driver
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import AzureOpenAI
import streamlit as st
from streamlit_chat import message
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_agraph.config import Config, ConfigBuilder

# Load environment variables from .env file (override=True forces reload)
load_dotenv(override=True)

# Neo4j connection
host = os.getenv('NEO4J_HOST')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')
driver = GraphDatabase.driver(host, auth=(user, password))

# OpenAI connection (Azure)
client = AzureOpenAI(
    api_version=os.getenv('OPENAI_API_VERSION', '2024-12-01-preview'),
    azure_endpoint=os.getenv('OPENAI_API_BASE'),
    api_key=os.getenv('OPENAI_API_KEY')
)


def check_connections():
    """
    Check Neo4j and OpenAI connections.
    Returns a tuple of (neo4j_status, openai_status, error_messages)
    """
    neo4j_ok = False
    openai_ok = False
    errors = []
    
    # Check Neo4j connection
    try:
        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            result.single()
            neo4j_ok = True
    except Exception as e:
        errors.append(f"Neo4j connection failed: {str(e)}")
    
    # Check OpenAI connection
    try:
        # Force reload environment variables
        load_dotenv(override=True)
        deployment_name = os.getenv('OPENAI_DEPLOYMENT_NAME', 'gpt-35-turbo')
        
        test_response = client.chat.completions.create(
            model=deployment_name,
            max_tokens=5,
            messages=[{"role": "user", "content": "test"}]
        )
        openai_ok = True
    except Exception as e:
        error_msg = str(e)
        errors.append(f"OpenAI connection failed: {error_msg}")
        errors.append(f"Deployment used: {deployment_name}")
        errors.append(f"Deployment from env: {os.getenv('OPENAI_DEPLOYMENT_NAME')}")
        errors.append(f"Endpoint: {os.getenv('OPENAI_API_BASE')}")
        
        # Provide helpful suggestions based on error type
        if "404" in error_msg or "DeploymentNotFound" in error_msg:
            errors.append("→ The deployment name might be incorrect.")
            errors.append("→ Check Azure Portal > Azure OpenAI > Deployments for the exact name.")
        elif "401" in error_msg or "Unauthorized" in error_msg:
            errors.append("→ API key might be incorrect or expired.")
        elif "endpoint" in error_msg.lower():
            errors.append("→ Check that OPENAI_API_BASE is correct.")
    
    return neo4j_ok, openai_ok, errors


def read_query(query, params={}):
    with driver.session() as session:
        result = session.run(query, params)
        response = [r.values()[0] for r in result]
        return response

def read_graph(messages):
    # create
    nodes = []
    edges = []
    for name in messages:
        name = name.split("LINK:")[0].strip()
        nodes.append({"id":name, "label":"Dataset"})
        new_query = """
        MATCH (a:Dataset)-[r]-(connectedNodes)
        WHERE a.name = $datasetName
        RETURN labels(connectedNodes) AS NodeType, connectedNodes.name AS ConnectedNode, type(r) AS RelationType  
        """
        with driver.session() as session:
            result = session.run(new_query, {"datasetName":name})
            for rel in result:
                this_rel = {"source":name, "label":rel["RelationType"], "target":rel["ConnectedNode"]}
                edges.append(this_rel)
                nodes.append({"id":rel["ConnectedNode"], "label":rel["NodeType"][0]})
    # format (also remove duplicate)
    formatted_nodes, formatted_edges = [], []
    nodes_seen = set()
    nodes_color = {"Dataset":"#4e79a7",
                    "Term":"#bab0ac",
                    "Location":"#edc948",
                    "Series":"#b07aa1",
                    "Funder":"#59a14f",
                    "Owner":"#e15759",
                    "Publication":"#f28e2b"}
    for node in nodes:
        if node["id"] not in nodes_seen:
            nodes_seen.add(node["id"])
            formatted_nodes.append(Node(id=node["id"], label=node["label"], size=25, shape="dot", color=nodes_color[node["label"]])) 
    for edge in edges:
        formatted_edges.append(Edge(source=edge["source"], label=["label"], target=edge["target"])) 

    return formatted_nodes, formatted_edges


### example cypher
examples = """
# What are the latest datasets?
MATCH (a:Dataset) RETURN a.name + " LINK: " + a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the most cited datasets?
MATCH (a:Dataset) RETURN a.name + " LINK: " + a.url AS response ORDER BY a.dataRefCount DESC LIMIT 3
# What are the most used datasets?
MATCH (a:Dataset) RETURN a.name + " LINK: " +  a.url AS response ORDER BY a.dataUserCount DESC LIMIT 3
# What are the latest datasets not owned by ICPSR?
MATCH (a:Dataset) WHERE a.owner <> 'ICPSR' RETURN a.name + " LINK: " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets about alcohol?
MATCH (a:Dataset) WHERE a.name CONTAINS 'alcohol' RETURN a.name + " LINK: " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets that mention alcohol?
MATCH (a:Dataset)-[:HAS_TERM]->(t:Term) WHERE t.name CONTAINS 'alcohol' RETURN a.name + " LINK: " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets in the United States Historical Election Returns Series?
MATCH (a:Dataset)-[:HAS_SERIES]->(s:Series) WHERE s.name = 'United States Historical Election Returns Series' RETURN a.name + " LINK: " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets onwed by ICPSR?
MATCH (a:Dataset)-[:HAS_OWNER]->(o:Owner) WHERE o.name = 'ICPSR' RETURN a.name + " LINK: " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets funder by National Science Foundation?
MATCH (a:Dataset)-[:HAS_FUNDER]->(f:Funder) WHERE f.name = "National Science Foundation" RETURN a.name + " LINK: " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets funder by government?
MATCH (a:Dataset)-[:HAS_FUNDER]->(f:Funder) WHERE f.type = "government" RETURN a.name + " LINK: " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets that include data from United States?
MATCH (a:Dataset)-[:HAS_LOCATION]->(l:Location) WHERE (l.name = "United States" OR l.name = "U.S.") RETURN a.name + " LINK: " +  a.url AS response ORDER BY a.date DESC LIMIT 3
# What are the latest datasets that include country level data?
MATCH (a:Dataset)-[:HAS_LOCATION]->(l:Location) WHERE l.type = "country" RETURN a.name + " LINK: " +  a.url AS response ORDER BY a.date DESC LIMIT 3
"""

### eg
# prompt_eg = "What are the earlest datasets?"
# prompt_input=examples_eg + "\n#" + prompt_eg
# completions = client.chat.completions.create(
#     model=os.getenv('OPENAI_DEPLOYMENT_NAME', 'gpt-3.5-turbo'),
#     max_tokens=1000,
#     n=1,
#     stop=None,
#     temperature=0.5,
#     messages=[{"role": "user", "content": prompt_input}]
# )
# cypher_query = completions.choices[0].message.content
# message = read_query(cypher_query)
# print(message)
# print(cypher_query)


st.title("DataChat: Chat with ICPSR Datasets")

# Check connections and display status in sidebar
with st.sidebar:
    st.header("Connection Status")
    if st.button("Check Connections"):
        with st.spinner("Checking connections..."):
            neo4j_ok, openai_ok, errors = check_connections()
            
            if neo4j_ok:
                st.success("✅ Neo4j: Connected")
            else:
                st.error("❌ Neo4j: Disconnected")
            
            if openai_ok:
                st.success("✅ OpenAI: Connected")
            else:
                st.error("❌ OpenAI: Disconnected")
            
            if errors:
                st.error("**Error Details:**")
                for error in errors:
                    st.text(error)

def generate_response(prompt):
    #prompt_eg = "What are the earlest datasets?"
    prompt_input=examples + "\n#" + prompt
    completions = client.chat.completions.create(
        model=os.getenv('OPENAI_DEPLOYMENT_NAME', 'gpt-3.5-turbo'),
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.5,
        messages=[{"role": "user", "content": prompt_input}]
    )
    cypher_query = completions.choices[0].message.content
    message = read_query(cypher_query) # list of string
    nodes, edges = read_graph(message)
    return message, nodes, edges, cypher_query

# Storing the chat
if 'generated' not in st.session_state:
    st.session_state['generated'] = []

if 'past' not in st.session_state:
    st.session_state['past'] = []

if 'graph' not in st.session_state:
    st.session_state['graph'] = []

def get_text():
    input_text = st.text_input(
        "Feel free to ask a question about ICPSR datasets", "", key="input")
    return input_text


tab1, tab2 = st.tabs(["🤖 DataChatBot", "🌐 DataChatViz"])

tab1.subheader("Datasets with links")
tab2.subheader("Interactive graphs")

user_input = get_text()
if user_input:
    output, nodes, edges, cypher_query = generate_response(user_input)

    with tab1:
        col1, col2 = st.columns([2, 1])

        with col2:
            another_placeholder = st.empty()
        with col1:
            placeholder = st.empty()

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

    with tab2:
        config = Config(width=750,
                        height=950,
                        directed=True, 
                        physics=True, 
                        hierarchical=False,
                        # **kwargs
                        )
        st.session_state.graph.append(agraph(nodes=nodes, edges=edges, config=config))

###### Saved earlier version

# tab1, tab2 = st.tabs(["🤖 DataChatBot", "🌐 DataChatViz"])

# tab1.subheader("DataChatBot")
# tab2.subheader("DataChatViz")

# col1, col2 = st.columns([2, 1])

# with col2:
#     another_placeholder = st.empty()
# with col1:
#     placeholder = st.empty()
# user_input = get_text()

# config = Config(width=750,
#                 height=950,
#                 directed=True, 
#                 physics=True, 
#                 hierarchical=False,
#                 # **kwargs
#                 )

# if user_input:
#     output, nodes, edges, cypher_query = generate_response(user_input)
#     # store the output
#     st.session_state.past.append(user_input)
#     st.session_state.generated.append((output, cypher_query))
#     st.session_state.graph.append(agraph(nodes=nodes, edges=edges, config=config))

# # Message placeholder
# with placeholder.container():
#     if st.session_state['generated']:
#         message(st.session_state['past'][-1],
#                 is_user=True, key=str(-1) + '_user')
#         for j, text in enumerate(st.session_state['generated'][-1][0]):
#             message(text, key=str(-1) + str(j))

# # Generated Cypher statements
# with another_placeholder.container():
#     if st.session_state['generated']:
#         st.text_area("Generated Cypher statement",
#                      st.session_state['generated'][-1][1], height=240)



