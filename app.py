import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

st.set_page_config(page_title="Spatial Voting Chaos", layout="wide")

# ==========================================
# Mathematical Core
# ==========================================

def get_majority_margin(p_test, p_base, voters):
    """Returns the vote margin of p_test against p_base. Positive means p_test wins."""
    dist_base = np.sum((voters - p_base)**2, axis=1)
    dist_test = np.sum((voters - p_test)**2, axis=1)
    votes_test = np.sum(dist_test < dist_base)
    votes_base = np.sum(dist_base < dist_test)
    return votes_test - votes_base

def generate_base_voters(n_voters=105):
    """Generates 3 factions of voters to guarantee structural cycles (Empty Core)."""
    centers = np.array([[0, 0.7], [-0.7, -0.4], [0.7, -0.4]])
    voters = []
    for i in range(n_voters):
        center = centers[i % 3]
        v = center + np.random.normal(0, 0.25, 2)
        voters.append(v)
    return np.array(voters)

def apply_polarization(base_voters, p):
    """Projects voters towards the diagonal line y=x."""
    voters = np.copy(base_voters)
    if p > 0:
        line_dir = np.array([1, 1]) / np.sqrt(2)
        for i in range(len(voters)):
            v = voters[i]
            proj_len = np.dot(v, line_dir)
            proj_point = proj_len * line_dir
            voters[i] = (1 - p) * v + p * proj_point
    return voters

def generate_packages(num_packages):
    """Places packages in a wide circular pattern with jitter to encompass the core."""
    angles = np.linspace(0, 2*np.pi, num_packages, endpoint=False)
    radius = 0.6
    packages = []
    for angle in angles:
        x = radius * np.cos(angle) + np.random.uniform(-0.1, 0.1)
        y = radius * np.sin(angle) + np.random.uniform(-0.1, 0.1)
        packages.append([x, y])
    return np.array(packages)

# ==========================================
# State Management
# ==========================================

if 'base_voters' not in st.session_state:
    st.session_state.base_voters = generate_base_voters()
if 'packages' not in st.session_state:
    st.session_state.packages = generate_packages(3)
if 'num_packages' not in st.session_state:
    st.session_state.num_packages = 3

# ==========================================
# UI Layout
# ==========================================

st.title("Latent Space Polarization & McKelvey Chaos Simulation")

with st.sidebar:
    st.header("Simulation Parameters")
    polarization = st.slider("Voter Polarization", 0.0, 1.0, 0.0, 0.01,
                             help="0 = 3 distinct factions (High Curl). 1 = 1D Ideological Line (Pure Gradient).")
    
    num_packages = st.slider("Number of Packages", 3, 10, 3)
    if num_packages != st.session_state.num_packages:
        st.session_state.packages = generate_packages(num_packages)
        st.session_state.num_packages = num_packages
        
    if st.button("Regenerate Random Layout"):
        st.session_state.base_voters = generate_base_voters()
        st.session_state.packages = generate_packages(num_packages)

# Calculate active state
active_voters = apply_polarization(st.session_state.base_voters, polarization)
packages = st.session_state.packages
labels = [chr(65+i) for i in range(len(packages))]

# ==========================================
# Visualization Engine
# ==========================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Continuous Trait Space & Vector Field")
    fig1, ax1 = plt.subplots(figsize=(7, 7))
    ax1.set_xlim(-1.2, 1.2)
    ax1.set_ylim(-1.2, 1.2)
    ax1.set_aspect('equal')
    ax1.grid(True, linestyle='--', alpha=0.3)
    
    # Plot Voters
    ax1.scatter(active_voters[:, 0], active_voters[:, 1], color='blue', alpha=0.3, s=20, label='Voters')
    
    # Plot Continuous Vector Field (360-Degree Win-Set Average)
    grid_res = 12
    X, Y = np.meshgrid(np.linspace(-1.1, 1.1, grid_res), np.linspace(-1.1, 1.1, grid_res))
    U, V = np.zeros_like(X), np.zeros_like(Y)
    
    angles = np.linspace(0, 2*np.pi, 16, endpoint=False)
    test_dirs = np.array([np.cos(angles), np.sin(angles)]).T
    step_size = 0.05
    
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            base_point = np.array([X[i, j], Y[i, j]])
            winning_dirs = []
            
            for d in test_dirs:
                test_point = base_point + step_size * d
                if get_majority_margin(test_point, base_point, active_voters) > 0:
                    winning_dirs.append(d)
            
            if winning_dirs:
                avg_dir = np.mean(winning_dirs, axis=0)
                norm = np.linalg.norm(avg_dir)
                if norm > 0:
                    U[i, j] = avg_dir[0] / norm
                    V[i, j] = avg_dir[1] / norm

    ax1.quiver(X, Y, U, V, color='gray', alpha=0.6, width=0.005)
    
    # Plot Packages
    ax1.scatter(packages[:, 0], packages[:, 1], color='red', s=150, zorder=5, edgecolor='black')
    for i, txt in enumerate(labels):
        ax1.annotate(txt, (packages[i, 0]+0.05, packages[i, 1]+0.05), fontsize=14, weight='bold')

    st.pyplot(fig1)

with col2:
    st.subheader("2. Discrete Hodge Graph (Tournament)")
    fig2, ax2 = plt.subplots(figsize=(7, 7))
    
    G = nx.DiGraph()
    for label in labels:
        G.add_node(label)
        
    for i in range(len(packages)):
        for j in range(len(packages)):
            if i == j: continue
            margin = get_majority_margin(packages[i], packages[j], active_voters)
            if margin > 0:
                G.add_edge(labels[i], labels[j])
                
    # Detect Cycles
    try:
        cycles = list(nx.simple_cycles(G))
        cyclic_edges = set()
        for cycle in cycles:
            for k in range(len(cycle)):
                cyclic_edges.add((cycle[k], cycle[(k+1) % len(cycle)]))
        is_cyclic = len(cycles) > 0
    except nx.NetworkXNoCycle:
        is_cyclic = False
        cyclic_edges = set()

    if is_cyclic:
        st.error(f"Topology: Intransitive Condorcet Cycle Detected ({len(cycles)} cycles)")
        edge_colors = ['red' if edge in cyclic_edges else 'black' for edge in G.edges()]
        node_color = '#ffcccc'
    else:
        st.success("Topology: Strictly Transitive Hierarchy")
        edge_colors = ['black' for edge in G.edges()]
        node_color = '#ccffcc'

    pos = nx.circular_layout(G)
    nx.draw(G, pos, ax=ax2, with_labels=True, node_color=node_color, 
            node_size=2500, font_size=16, font_weight='bold', 
            edge_color=edge_colors, arrowsize=25, width=2.5, connectionstyle='arc3,rad=0.1')
    
    st.pyplot(fig2)
