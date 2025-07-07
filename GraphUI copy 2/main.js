document.addEventListener('DOMContentLoaded', () => {
    const graphManager = new GraphManager();
    const chatManager = new ChatManager();
    
    // 获取DOM元素
    const messageInput = document.getElementById('messageInput');
    const submitButton = document.getElementById('submitMessage');
    const confirmButton = document.getElementById('confirmGraph');
    const saveVersionButton = document.getElementById('saveVersion');
    const downloadButton = document.getElementById('downloadHistory');
    const versionSelect = document.getElementById('versionSelect');
    const modifyInput = document.getElementById('modifyInput');
    const modifyButton = document.getElementById('modifyButton');

    // Helper function to log user actions with timestamp
    function logUserAction(action) {
        const timestamp = new Date().toISOString();
        console.log(`${timestamp} User doing: ${action}`);
    }



    // Added handler for the modify button
    modifyButton.addEventListener('click', async () => {
        const text = modifyInput.value.trim();
        if (text && graphManager.oldGraph) {
            logUserAction(`Modified graph with text: "${text}"`);
            try {
                // Make a deep copy of the current graph state to avoid reference issues
                const currentGraphState = JSON.parse(JSON.stringify(graphManager.oldGraph));
                
                // Convert to API format, preserving all edges and nodes
                const apiFormatGraph = {
                    nodes: currentGraphState.nodes.map(node => ({
                        id: node.id,
                        description: node.label || ""
                    })),
                    links: currentGraphState.edges.map(edge => ({
                        source: typeof edge.source === 'object' ? edge.source.id : edge.source,
                        target: typeof edge.target === 'object' ? edge.target.id : edge.target,
                        type: edge.label || ""
                    }))
                };
                
                const response = await fetch('http://localhost:5002/api/modify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        userInput: text,
                        newGraph: apiFormatGraph
                    })
                });
                
                const result = await response.json();
                
                if (result.status === "success" && result.graph) {
                    // Store both graphs - consistent with submitButton handler
                    graphManager.newGraph = result.graph;
                    graphManager.simGraph = result.sim_graph;
                    
                    // Find common nodes between sim_graph and new_graph
                    const commonNodeIds = new Set();
                    if (result.graph && result.sim_graph) {
                        const simNodeIds = new Set(result.sim_graph.nodes.map(n => n.id));
                        result.graph.nodes.forEach(node => {
                            if (simNodeIds.has(node.id)) {
                                commonNodeIds.add(node.id);
                            }
                        });
                    }
                    
                    // Identify modified nodes based on text content
                    const modifiedNodeIds = new Set();
                    if (text.toLowerCase().includes("modify") || text.toLowerCase().includes("change")) {
                        // Parse text for mentioned node IDs
                        const nodeIdRegex = /Node\d+/g;
                        const mentionedNodeIds = text.match(nodeIdRegex) || [];
                        mentionedNodeIds.forEach(id => modifiedNodeIds.add(id));
                    }
                    
                    // Format the graphs for rendering
                    const formattedNewGraph = graphManager.convertGraphFormat(result.graph);
                    const formattedSimGraph = graphManager.convertGraphFormat(result.sim_graph);
                    
                    // Render new_graph to top panel with editing enabled but extension disabled
                    graphManager.renderGraph(
                        graphManager.oldGraphSvg, 
                        formattedNewGraph, 
                        true,                // Enable editing
                        true,                // Initial render
                        1,                   // Normal scale
                        commonNodeIds,       // Pass common node IDs for highlighting
                        true,                // Disable extension functionality
                        false,               // Enable editing
                        modifiedNodeIds      // Pass modified node IDs
                    );
                    
                    // Render sim_graph to bottom panel with extension enabled but editing disabled
                    graphManager.renderGraph(
                        graphManager.currentGraphSvg,
                        formattedSimGraph,
                        true,                // Keep as true to allow extension
                        true,                // Initial render
                        1,                   // Normal scale
                        commonNodeIds,       // Pass common node IDs for highlighting
                        false,               // Allow extension
                        true,                // Disable editing (node/edge addition/deletion)
                        null                 // No modified nodes initially
                    );
                    
                    // Update stored graphs
                    graphManager.currentGraph = formattedSimGraph;
                    graphManager.oldGraph = formattedNewGraph;
                    
                    modifyInput.value = '';
                } else {
                    console.error('Failed to modify graph:', result.message || 'Invalid response structure');
                }
            } catch (error) {
                console.error('Error modifying graph:', error);
            }
        }
    });

    // Modified submit button handler
    submitButton.addEventListener('click', async () => {
        const text = messageInput.value.trim();
        if (text) {
            logUserAction(`Submitted message: "${text}"`);
            chatManager.addMessage(text, 'user');
            messageInput.value = '';
            
            try {
                // Use the previously confirmed graph (oldGraph) as input for the next round
                const oldGraph = graphManager.oldGraph || null;

                // TODO: Uncomment for the server response.
                const response = await fetch('http://localhost:5002/api/graph_call', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        oldGraph: oldGraph,
                        userPrompt: text
                    })
                });
                const result = await response.json();
                // TODO: comment out the following line
                // result = testText;
                
                console.log('GraphCallFunction Result:', result);
                
                // Store both graphs
                graphManager.newGraph = result.graph;
                graphManager.simGraph = result.sim_graph;
                
                // Find common nodes between sim_graph and new_graph
                const commonNodeIds = new Set();
                if (result.graph && result.sim_graph) {
                    const simNodeIds = new Set(result.sim_graph.nodes.map(n => n.id));
                    result.graph.nodes.forEach(node => {
                        if (simNodeIds.has(node.id)) {
                            commonNodeIds.add(node.id);
                        }
                    });
                }
                
                // Format the graphs for rendering
                const formattedNewGraph = graphManager.convertGraphFormat(result.graph);
                const formattedSimGraph = graphManager.convertGraphFormat(result.sim_graph);
                
                // Render new_graph to top panel with editing enabled but extension disabled
                graphManager.renderGraph(
                    graphManager.oldGraphSvg, 
                    formattedNewGraph, 
                    true,  // Enable editing
                    true,  // Initial render
                    1,     // Normal scale
                    commonNodeIds,  // Pass common node IDs for highlighting
                    true,   // Disable extension functionality
                    false,  // Enable editing
                    null    // No modified nodes initially
                );
                
                // Render sim_graph to bottom panel with extension enabled but editing disabled
                graphManager.renderGraph(
                    graphManager.currentGraphSvg,
                    formattedSimGraph,
                    true,   // Keep as true to allow extension
                    true,   // Initial render
                    1,      // Normal scale
                    commonNodeIds,  // Pass common node IDs for highlighting
                    false,  // Allow extension
                    true,   // Disable editing (node/edge addition/deletion)
                    null    // No modified nodes initially
                );
                
                // Store the current graph
                graphManager.currentGraph = formattedSimGraph;
                graphManager.oldGraph = formattedNewGraph;
            } catch (error) {
                console.error('Failed to test GraphCallFunction:', error);
                logUserAction(`Error during message submission: ${error.message}`);
            }
        }
    });

    // Update save version functionality to properly save both graphs
    saveVersionButton.addEventListener('click', () => {
        logUserAction('Saved graph version');
        if (graphManager.currentGraph && graphManager.newGraph) {
            const version = {
                number: ++graphManager.currentVersion,
                timestamp: Date.now(),
                simGraph: JSON.parse(JSON.stringify(graphManager.currentGraph)),
                newGraph: JSON.parse(JSON.stringify(graphManager.newGraph))
            };
            
            graphManager.versionHistory.push(version);
            
            const option = document.createElement('option');
            option.value = version.number;
            option.textContent = `Version ${version.number} (${new Date(version.timestamp).toLocaleTimeString()})`;
            versionSelect.appendChild(option);
            
            // Select the newly created version
            versionSelect.value = version.number;
        }
    });

    // Update load version functionality to properly load both graphs
    versionSelect.addEventListener('change', () => {
        const versionNumber = parseInt(versionSelect.value);
        logUserAction(`Loaded version ${versionNumber}`);
        if (!isNaN(versionNumber)) {
            const version = graphManager.versionHistory.find(v => v.number === versionNumber);
            if (version) {
                // Find common nodes
                const commonNodeIds = new Set();
                if (version.simGraph && version.simGraph.nodes && version.newGraph && version.newGraph.nodes) {
                    const simNodeIds = new Set(version.simGraph.nodes.map(n => n.id));
                    version.newGraph.nodes.forEach(node => {
                        if (simNodeIds.has(node.id)) {
                            commonNodeIds.add(node.id);
                        }
                    });
                }
                
                // Render both graphs with appropriate flags
                graphManager.renderGraph(
                    graphManager.oldGraphSvg, 
                    version.newGraph, 
                    true,   // Enable editing
                    false,  // Not initial render
                    1,      // Normal scale
                    commonNodeIds, // Common node highlighting
                    true    // Disable extension functionality
                );
                
                graphManager.renderGraph(
                    graphManager.currentGraphSvg, 
                    version.simGraph, 
                    true,   // Keep as true for consistency
                    false,  // Not initial render
                    1,      // Normal scale
                    commonNodeIds, // Common node highlighting
                    false,  // Allow extension
                    true    // Disable editing
                );
                
                // Update stored graphs
                graphManager.currentGraph = version.simGraph;
                graphManager.newGraph = version.newGraph;
            }
        }
    });

    // Update confirm graph logic - keep new_graph after confirmation
    confirmButton.addEventListener('click', async () => {
        logUserAction('Confirmed graph');
        // Get the current modified graph from the top-left panel
        const modifiedNewGraph = graphManager.oldGraph;
        
        // Check if there's a graph to confirm
        if (!modifiedNewGraph) {
            console.log("No graph to confirm. Please submit a message first.");
            return; // Exit early if there's no graph to confirm
        }
        
        try {
            console.log("Confirming modified graph:", modifiedNewGraph);
            
            // We don't need to call graph_update API anymore, just update our local reference
            graphManager.newGraph = modifiedNewGraph;
            
            // Get the last user message for context
            const lastUserMessage = chatManager.getLastUserMessage();
            
            // Call the LLM API with chat history and the modified graph
            try {
                const llmResponse = await fetch('http://localhost:5002/api/call_llm', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        chatHistory: chatManager.messages,
                        newGraph: modifiedNewGraph // Use the modified graph
                    })
                });
                
                const llmResult = await llmResponse.json();
                
                if (llmResult.status === "success") {
                    // Add the LLM response to chat
                    const formattedGraph = graphManager.convertGraphFormat(modifiedNewGraph);
                    chatManager.addMessage(llmResult.response, 'ai', formattedGraph);
                } else {
                    console.error('Failed to get LLM response:', llmResult.message);
                    chatManager.addMessage(`Graph confirmed! An error occurred when generating response.`, 'ai', graphManager.convertGraphFormat(modifiedNewGraph));
                }
            } catch (error) {
                console.error('Failed to call LLM API:', error);
                chatManager.addMessage(`Graph confirmed! Current graph has been updated.`, 'ai', graphManager.convertGraphFormat(modifiedNewGraph));
            }
            
            // Save chat history
            try {
                const historyResponse = await fetch('http://localhost:5002/api/save_history', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        timestamp: new Date().toISOString(),
                        userMessage: lastUserMessage?.text || '',
                        aiResponse: chatManager.messages[chatManager.messages.length - 1].text
                    })
                });
                const historyResult = await historyResponse.json();
                console.log('Save History Result:', historyResult);
            } catch (error) {
                console.error('Failed to save history:', error);
            }
            
            // Clear current graph area (sim graph area) without clearing newGraph
            graphManager.currentGraph = null;
            graphManager.simGraph = null; // Clear simGraph reference
            graphManager.currentGraphSvg.selectAll("*").remove();
            
            // Clear version select options and reset version history
            while (versionSelect.options.length > 1) {
                versionSelect.remove(1);
            }
            versionSelect.value = '';
            graphManager.versionHistory = [];
            graphManager.currentVersion = 0;
        } catch (error) {
            console.error('Error confirming graph:', error);
        }
    });

    // Download history with both graphs
    downloadButton.addEventListener('click', () => {
        logUserAction('Downloaded history');
        if (graphManager.versionHistory.length > 0) {
            const historyData = JSON.stringify(graphManager.versionHistory, null, 2);
            const blob = new Blob([historyData], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `graph_history_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    });

    // Support Enter key to send messages
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            logUserAction(`Submitted message with Enter key: "${messageInput.value.trim()}"`);
            submitButton.click();
        }
    });

    // Support Enter key for modify input
    modifyInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            logUserAction(`Modified graph with Enter key: "${modifyInput.value.trim()}"`);
            modifyButton.click();
        }
    });

    // Add this to close the context menu when clicking outside
    document.addEventListener('click', function(event) {
        const contextMenu = document.querySelector('.context-menu');
        if (contextMenu && !contextMenu.contains(event.target) && contextMenu.style.display !== 'none') {
            logUserAction('Closed context menu');
            contextMenu.style.display = 'none';
        }
    });
});