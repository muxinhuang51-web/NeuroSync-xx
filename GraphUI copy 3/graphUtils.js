class GraphManager {
    constructor() {
        this.oldGraphSvg = d3.select("#oldGraph");
        this.currentGraphSvg = d3.select("#currentGraph");
        this.currentGraph = null;
        this.oldGraph = null;
        this.newGraph = null; // Complete graph from backend
        this.simGraph = null; // Simplified graph from backend
        this.graphHistory = JSON.parse(localStorage.getItem('graphHistory') || '[]');
        this.versionHistory = []; // Store versions for current editing session
        this.currentVersion = 0;  // Track current version number
        this.extensionPreview = null;
        this.initExtensionPreview();

        // Add window unload event listener to save history to file
        window.addEventListener('beforeunload', () => {
            if (this.graphHistory.length > 0) {
                localStorage.setItem('graphHistory', JSON.stringify(this.graphHistory));
            }
        });
    }
    // Add logging function to track user actions
    logUserAction(action) {
        const timestamp = new Date().toISOString();
        console.log(`${timestamp} User doing: ${action}`);
    }
    
    initExtensionPreview() {
        // Create extension preview element
        this.extensionPreview = document.createElement('div');
        this.extensionPreview.className = 'extension-preview';
        this.extensionPreview.innerHTML = `
            <div class="extension-preview-header">
                <span>Extension Preview</span>
                <button class="close-button">×</button>
            </div>
            <div class="extension-preview-content"></div>
        `;
        document.body.appendChild(this.extensionPreview);

        // Add close button handler
        this.extensionPreview.querySelector('.close-button').addEventListener('click', () => {
            this.hideExtensionPreview();
        });

        // Add drag functionality
        const header = this.extensionPreview.querySelector('.extension-preview-header');
        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;

        header.addEventListener('mousedown', (e) => {
            isDragging = true;
            initialX = e.clientX - this.extensionPreview.offsetLeft;
            initialY = e.clientY - this.extensionPreview.offsetTop;
        });

        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                e.preventDefault();
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;
                this.extensionPreview.style.left = `${currentX}px`;
                this.extensionPreview.style.top = `${currentY}px`;
                this.extensionPreview.style.transform = 'none'; // Remove centering when dragging
            }
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    }

    showExtensionPreview(event, graph, sourceNode) {
        this.logUserAction("Viewing extension preview");
        if (!graph || !graph.nodes) {
            console.error('Invalid graph data');
            return;
        }

        const preview = this.extensionPreview;
        
        // Position settings
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        const previewWidth = 1200;
        const previewHeight = 900;
        
        // Calculate position to ensure the window fits on screen
        const left = Math.max(0, Math.min(windowWidth - 20, (windowWidth - previewWidth) / 2 + 10));
        const top = Math.max(0, Math.min(windowHeight - 20, (windowHeight - previewHeight) / 2 + 10));
        
        preview.style.display = 'block';
        preview.style.left = `${left}px`;
        preview.style.top = `${top}px`;
        preview.style.transform = 'none';
        
        // Get the content container
        const contentContainer = preview.querySelector('.extension-preview-content');
        contentContainer.innerHTML = '';
        
        // Format graph data with safety checks
        const formattedGraph = {
            nodes: graph.nodes.map(node => ({
                id: node.id || '',
                label: node.description || node.label || '',
                x: undefined,
                y: undefined
            })),
            edges: (graph.links || graph.edges || []).map(link => ({
                source: link.source || '',
                target: link.target || '',
                label: link.type || ''
            }))
        };

        // Create SVG and render graph with standard layout
        const svg = d3.select(contentContainer)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%');

        // CHANGE: Use the same optimizeGraphLayout as main graph area
        const optimizedGraph = this.optimizeGraphLayout(formattedGraph, 
            previewWidth - 60, 
            previewHeight - 130
        );

        // Render with the optimized graph - use same scale factor as main area
        this.renderGraph(
            svg, 
            optimizedGraph, 
            false,  // Not editable
            true,   // Initial render
            1.0,    // CHANGE: use same scale as main graph area
            null,   // No common nodes
            true,   // No extension
            true    // No editing
        );
    }

    hideExtensionPreview() {
        if (this.extensionPreview) {
            this.extensionPreview.style.display = 'none';
        }
    }

    // Convert between graph formats
    convertGraphFormat(graph) {
        // Handle null or undefined graph
        if (!graph) {
            return { nodes: [], edges: [] };
        }
        
        // Convert from backend format to the format used by D3
        return {
            nodes: (graph.nodes || []).map(node => ({
                id: node.id,
                label: node.description || node.label || `Node ${node.id}`,
                x: node.x || undefined,
                y: node.y || undefined,
                fx: node.fx || null,
                fy: node.fy || null,
                modified: node.modified || false
            })),
            edges: (graph.links || []).map(link => {
                // Handle both object references and string IDs
                const source = typeof link.source === 'object' ? link.source.id : link.source;
                const target = typeof link.target === 'object' ? link.target.id : link.target;
                
                return {
                    id: `edge-${source}-${target}`,
                    source: source,
                    target: target,
                    label: link.type || link.label || '',
                    modified: link.modified || false
                };
            })
        };
    }

    // GraphExtension method - modified to accept a node ID
    async GraphExtension(nodeId) {
        try {
            console.log(`Extending node: ${nodeId}`);
            const response = await fetch('http://localhost:5002/api/graph_extension', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    nodeId: nodeId
                })
            });
            const result = await response.json();
            if (result.status === 'success') {
                return result.data;
            } else {
                console.error('GraphExtension API returned error:', result.message);
                return null;
            }
        } catch (error) {
            console.error('Failed to call GraphExtension API:', error);
            return null;
        }
    }

    // New method to handle node extension clicks
    async handleNodeExtension(node) {
        try {
            // Extract node ID or index from the node
            const nodeId = node.id;
            this.logUserAction("Extending node");
            console.log(`Requesting extension for node: ${nodeId}`);
            
            // Call the extension API
            const extensionGraph = await this.GraphExtension(nodeId);
            
            if (extensionGraph) {
                this.showExtensionPreview(null, extensionGraph, node);
            } else {
                alert("无法获取节点扩展信息");
            }
        } catch (error) {
            console.error("Error during node extension:", error);
            alert("节点扩展功能出错");
        }
    }

    generateRandomGraph() {
        const nodeCount = Math.floor(Math.random() * 3) + 3; // 3-5 nodes
        const nodes = [];
        const edges = [];

        for (let i = 0; i < nodeCount; i++) {
            nodes.push({
                id: `node-${i}`,
                label: `Node ${i}`,
                x: Math.random() * 500,
                y: Math.random() * 300
            });
        }

        for (let i = 0; i < nodeCount - 1; i++) {
            edges.push({
                id: `edge-${i}`,
                source: nodes[i].id,
                target: nodes[i + 1].id,
                label: `Edge ${i}`
            });
        }

        return { nodes, edges };
    }

    // Helper method to compute node levels
    computeNodeLevels(graph) {
        const levels = new Map();
        const visited = new Set();
        
        // Find root nodes (nodes with no incoming edges)
        const hasIncomingEdge = new Set(graph.edges.map(e => 
            typeof e.target === 'string' ? e.target : e.target.id));
        const rootNodes = graph.nodes.filter(n => !hasIncomingEdge.has(n.id));

        // Perform BFS to assign levels
        let currentLevel = 0;
        let currentNodes = rootNodes;

        while (currentNodes.length > 0) {
            const nextNodes = new Set();
            currentNodes.forEach(node => {
                if (!visited.has(node.id)) {
                    visited.add(node.id);
                    levels.set(node.id, currentLevel);
                    
                    // Find children
                    graph.edges.forEach(edge => {
                        const sourceId = typeof edge.source === 'string' ? edge.source : edge.source.id;
                        const targetId = typeof edge.target === 'string' ? edge.target : edge.target.id;
                        
                        if (sourceId === node.id) {
                            const targetNode = graph.nodes.find(n => n.id === targetId);
                            if (targetNode) nextNodes.add(targetNode);
                        }
                    });
                }
            });
            currentNodes = Array.from(nextNodes);
            currentLevel++;
        }

        // Handle any remaining nodes (for cyclic graphs)
        graph.nodes.forEach(node => {
            if (!levels.has(node.id)) {
                levels.set(node.id, currentLevel);
            }
        });

        return levels;
    }

    renderGraph(svg, graph, isEditable, isInitialRender = false, previewScale = 1, commonNodeIds = null, disableExtension = false, disableEditing = false, modifiedNodeIds = null) {
        // Store reference to this for use in closures
        const self = this;
        
        if (!graph) return;
    
        svg.selectAll("*").remove();
        const width = svg.node().clientWidth || 800; // Fallback width
        const height = svg.node().clientHeight || 600; // Fallback height
        
        // Check if we're rendering in extension preview by examining parent elements
        const isExtensionPreview = svg.node().parentNode.classList.contains('extension-preview-content');
        
        // Define arrowhead marker with unique ID to prevent conflicts between multiple SVGs
        const markerId = "arrowhead-" + Math.random().toString(36).substr(2, 9);
        svg.append("defs").append("marker")
            .attr("id", markerId)
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 20)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("fill", "#999");
    
        // Node and text size - CONSISTENT SIZE for both views
        const nodeRadius = 25 * previewScale;
        const fontSize = 12 * previewScale; // CHANGE: Same font size regardless of preview
        
        // Node dimensions - CONSISTENT SIZE for both views
        const nodeWidth = 120 * previewScale;  // CHANGE: Same width regardless of preview
        const nodeHeight = 50 * previewScale;  // CHANGE: Same height regardless of preview
        const cornerRadius = 10 * previewScale;
        
        // Create node map for reference
        const nodeMap = {};
        graph.nodes.forEach(node => {
            nodeMap[node.id] = node;
        });
    
        // Ensure edges have proper references
        graph.edges.forEach(edge => {
            if (typeof edge.source === 'string') {
                edge.source = nodeMap[edge.source] || edge.source;
            }
            if (typeof edge.target === 'string') {
                edge.target = nodeMap[edge.target] || edge.target;
            }
        });
    
        // Reset positions for initial render
        if (isInitialRender) {
            // Clear any previous fixed positions
            graph.nodes.forEach(node => {
                node.fx = null;
                node.fy = null;
            });
            
            // CHANGE: Use the same layout algorithm for both views
            graph = self.optimizeGraphLayout(graph, width, height);
        }
    
        // Simulation parameters - CONSISTENT for both views
        // const simulation = d3.forceSimulation(graph.nodes)
        //     .force("link", d3.forceLink(graph.edges)
        //         .id(d => d.id)
        //         .distance(220)) // CHANGE: Same distance regardless of preview
        //     .force("charge", d3.forceManyBody()
        //         .strength(-500)) // CHANGE: Same strength regardless of preview
        //     .force("center", d3.forceCenter(width / 2, height / 2)
        //         .strength(0.02))
        //     .force("x", d3.forceX().x(d => d.fx || width/2).strength(0.08))
        //     .force("y", d3.forceY().y(d => d.fy || height/2).strength(0.08))
        //     .force("collide", d3.forceCollide(Math.sqrt(nodeWidth*nodeWidth + nodeHeight*nodeHeight)/2 + 25)) // CHANGE: Same collision radius
        //     .on("tick", ticked);
    
        // FIX: Properly create edge paths
        const edgePaths = svg.selectAll('.edge')
            .data(graph.edges)
            .enter()
            .append('path')
            .attr('class', 'edge')
            .attr('marker-end', `url(#${markerId})`)
            .style('stroke', '#999')
            .style('stroke-width', '1.5px')
            .style('fill', 'none');
    
        // FIX: Properly create edge labels
        const edgeLabels = svg.selectAll('.edge-label')
            .data(graph.edges)
            .enter()
            .append('g')
            .attr('class', 'edge-label');
            
        edgeLabels.append('text')
            .text(d => d.label || d.type || '')
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'central')
            .style('font-size', fontSize + 'px')
            .style('fill', '#666');
    
        // Add edge label editing functionality  
        if (isEditable && !disableEditing) {
            // Add double-click handler for edge labels
            console.log(`Extending node: we are editing link`);
            edgeLabels.selectAll('text').on('dblclick', function(event, d) {
                event.preventDefault();
                event.stopPropagation();
                
                // Get the current position and text
                const currentLabel = d.label || d.type || '';
                const bbox = this.getBoundingClientRect();
                const svgRect = svg.node().getBoundingClientRect();
                
                // Create an input field for editing
                const foreignObject = svg.append('foreignObject')
                    .attr('x', bbox.x - svgRect.x - 50) // Center the input field
                    .attr('y', bbox.y - svgRect.y - 15) // Position slightly above
                    .attr('width', 100)
                    .attr('height', 30)
                    .style('overflow', 'visible')
                    .attr('class', 'edge-editor');
                
                const input = foreignObject.append('xhtml:input')
                    .attr('type', 'text')
                    .attr('value', currentLabel)
                    .style('width', '100%')
                    .style('height', '100%')
                    .style('font-size', fontSize + 'px')
                    .style('border', '1px solid #3498db')
                    .style('border-radius', '4px')
                    .style('padding', '2px 4px')
                    .style('text-align', 'center');
                
                // Focus the input field
                input.node().focus();
                input.node().select();
                
                // Handle Enter key press
                input.on('keypress', function(event) {
                    if (event.key === 'Enter') {
                        event.preventDefault();
                        this.blur();
                    }
                });
                
                // Handle blur event
                input.on('blur', function() {
                    self.logUserAction("Changed edge label");
                    // Update the edge label
                    const newLabel = this.value.trim();
                    d.label = newLabel;
                    d.type = newLabel; // Update type for consistency
                    
                    // Update the label text
                    d3.select(edgeLabels.nodes()[graph.edges.indexOf(d)])
                      .select('text')
                      .text(newLabel);
                    
                    // Remove the input field
                    foreignObject.remove();
                    
                    // Trigger a simulation tick to update positions
                    simulation.alpha(0.1).restart();
                });
            });
        }
    
        // Adjust simulation parameters based on context
        const simulation = d3.forceSimulation(graph.nodes)
            .force("link", d3.forceLink(graph.edges)
                .id(d => d.id)
                .distance(isExtensionPreview ? 150 : 220))
            .force("charge", d3.forceManyBody()
                .strength(isExtensionPreview ? -300 : -500))
            .force("center", d3.forceCenter(width / 2, height / 2)
                .strength(0.02))
            .force("x", d3.forceX().x(d => d.fx || width/2).strength(0.08))
            .force("y", d3.forceY().y(d => d.fy || height/2).strength(0.08))
            .force("collide", d3.forceCollide(Math.sqrt(nodeWidth*nodeWidth + nodeHeight*nodeHeight)/2 + (isExtensionPreview ? 15 : 25)))
            .on("tick", ticked);
    
        // Draw nodes
        const nodes = svg.selectAll('.node')
            .data(graph.nodes)
            .enter()
            .append('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
    
        // Add rounded rectangle nodes with conditional fill color
        nodes.append('rect')
            .attr('width', nodeWidth)
            .attr('height', nodeHeight)
            .attr('rx', cornerRadius)
            .attr('ry', cornerRadius)
            .attr('x', -nodeWidth / 2)
            .attr('y', -nodeHeight / 2)
            .style('fill', d => {
                if (modifiedNodeIds && modifiedNodeIds.has(d.id)) {
                    return '#ffeedb'; // Light orange for modified nodes
                } else if (commonNodeIds && commonNodeIds.has(d.id)) {
                    return '#e3f2fd'; // Light blue for common nodes
                }
                return 'white';
            })
            .style('stroke', d => {
                if (modifiedNodeIds && modifiedNodeIds.has(d.id)) {
                    return '#ff9800'; // Orange border for modified nodes
                } else if (commonNodeIds && commonNodeIds.has(d.id)) {
                    return '#2196f3';
                }
                return '#ccc';
            })
            .style('stroke-width', d => {
                if (modifiedNodeIds && modifiedNodeIds.has(d.id)) {
                    return '2.5px';  // Thicker border for modified nodes
                } 
                return '1px';
            });
    
        // Add extension indicator if enabled
        if (isEditable && !disableExtension) {
            nodes.filter(d => !d.isExtended)
                .append('circle')
                .attr('class', 'extension-indicator')
                .attr('r', 8)
                .attr('cx', nodeRadius - 5)
                .attr('cy', -nodeRadius + 5)
                .style('fill', '#4caf50')
                .style('stroke', 'white')
                .style('stroke-width', '1px')
                .style('cursor', 'pointer')
                .on('click', function(event, d) {
                    event.stopPropagation();
                    self.handleNodeExtension(d);
                });
            
            nodes.filter(d => !d.isExtended)
                .append('text')
                .attr('class', 'extension-symbol')
                .attr('x', nodeRadius - 5)
                .attr('y', -nodeRadius + 5)
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'central')
                .text('+')
                .style('fill', 'white')
                .style('font-size', '14px')
                .style('pointer-events', 'none');
        }
    
        // Add node labels with proper centering in rectangles
        const nodeLabels = nodes.append('text')
            .attr('class', 'node-label')
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle') // Center text vertically
            .attr('dy', '0.1em') // Small adjustment for visual centering
            .style('font-size', fontSize + 'px')
            .style('fill', '#333');
    
        // Split text into multiple lines if needed
        nodeLabels.each(function(d) {
            const text = d3.select(this);
            const label = d.label || '';
            const lineHeight = 1.1;
            
            // Detect if we're in extension preview
            const isExtensionPreview = text.node().ownerSVGElement.parentNode.classList.contains('extension-preview-content');
            
            // Different handling for Chinese vs Latin characters
            const isMostlyChinese = /[\u4e00-\u9fa5]/.test(label) && 
                                   (label.match(/[\u4e00-\u9fa5]/g) || []).length > label.length / 3;
            
            let lines = [];
            
            if (isMostlyChinese) {
                // For Chinese text, break every 8-10 characters (fewer in extension preview)
                const charsPerLine = isExtensionPreview ? 8 : 10;
                for (let i = 0; i < label.length; i += charsPerLine) {
                    lines.push(label.substring(i, i + charsPerLine));
                }
            } else {
                // For Latin text, break by words with character limit
                const words = label.split(/\s+/).filter(Boolean);
                if (words.length === 0) return;
                
                let currentLine = words[0];
                const charLimit = isExtensionPreview ? 12 : 15; // Shorter line length in extension preview
                
                for (let i = 1; i < words.length; i++) {
                    const word = words[i];
                    const testLine = currentLine + " " + word;
                    
                    if (testLine.length <= charLimit) {
                        currentLine = testLine;
                    } else {
                        lines.push(currentLine);
                        currentLine = word;
                    }
                }
                lines.push(currentLine);
            }
            
            // In extension preview, limit lines to 2 with ellipsis if needed
            if (isExtensionPreview && lines.length > 2) {
                lines = lines.slice(0, 2);
                lines[1] = lines[1].substring(0, 6) + '...';
            }
            
            // Clear existing text
            text.text(null);
            
            // Calculate vertical offset to center all lines within node
            const totalHeight = (lines.length - 1) * lineHeight;
            const verticalOffset = -totalHeight / 2;
            
            // Add each line as a tspan element
            lines.forEach((line, i) => {
                text.append("tspan")
                    .attr("x", 0)
                    .attr("y", verticalOffset)
                    .attr("dy", `${i * lineHeight}em`)
                    .text(line);
            });
        });
    
        // Add editing functionality for nodes
        if (isEditable && !disableEditing) {
            // Double-click to edit node label
            nodes.on('dblclick', function(event, d) {
                event.preventDefault();
                const currentLabel = d.label;
                const newLabel = prompt("Edit node label:", currentLabel);
                if (newLabel !== null && newLabel !== currentLabel) {
                    self.logUserAction("Changed node label");
                    d.label = newLabel;
                    
                    // Update the label in the newGraph structure for backend communication
                    if (self.newGraph && self.newGraph.nodes) {
                        const backendNode = self.newGraph.nodes.find(n => n.id === d.id);
                        if (backendNode) {
                            backendNode.description = newLabel;
                            backendNode.modified = true; // Mark as modified
                        }
                    }
                    
                    // Update the visible label
                    d3.select(this).select('.node-label').each(function() {
                        const text = d3.select(this);
                        const words = newLabel.split(/\s+/).filter(Boolean);
                        const lineHeight = 1.1;
                        const lineLimit = 20; // Characters per line
                        
                        let lines = [];
                        let currentLine = words[0] || '';
                        
                        for (let i = 1; i < words.length; i++) {
                            const word = words[i];
                            const testLine = currentLine + " " + word;
                            
                            if (testLine.length <= lineLimit) {
                                currentLine = testLine;
                            } else {
                                lines.push(currentLine);
                                currentLine = word;
                            }
                        }
                        lines.push(currentLine);
                        
                        text.text(null); // Clear existing text
                        
                        lines.forEach((line, i) => {
                            text.append("tspan")
                                .attr("x", 0)
                                .attr("y", 0)
                                .attr("dy", `${i * lineHeight}em`)
                                .text(line);
                        });
                        
                        // Adjust vertical position
                        const totalHeight = (lines.length - 1) * lineHeight;
                        text.attr('dy', nodeRadius + 5 + (totalHeight / 2) + 'em');
                    });
                    
                    // Update highlight for modified node
                    const modifiedIds = new Set(modifiedNodeIds || []);
                    modifiedIds.add(d.id);
                    d3.select(this).select('circle')
                        .style('fill', '#ffeb3b')
                        .style('stroke', '#ffc107')
                        .style('stroke-width', '2.5px');
                }
            });
            
            // Add context menu for nodes (delete option)
            nodes.on('contextmenu', function(event, d) {
                event.preventDefault();
                
                // Create or clear context menu
                const contextMenu = d3.select('.context-menu');
                contextMenu.html('');
                contextMenu
                    .style('display', 'block')
                    .style('left', (event.pageX) + 'px')
                    .style('top', (event.pageY) + 'px');
                
                // Delete node option
                contextMenu.append('div')
                    .text('Delete Node')
                    .on('click', () => {
                        self.logUserAction("Deleted node");
                        // Remove node from graph data
                        const nodeIndex = graph.nodes.findIndex(n => n.id === d.id);
                        if (nodeIndex >= 0) {
                            graph.nodes.splice(nodeIndex, 1);
                        }
                        
                        // Remove connected edges
                        graph.edges = graph.edges.filter(edge => 
                            (typeof edge.source === 'object' ? edge.source.id !== d.id : edge.source !== d.id) && 
                            (typeof edge.target === 'object' ? edge.target.id !== d.id : edge.target !== d.id)
                        );
                        
                        // Update backend graph structure
                        if (self.newGraph) {
                            if (self.newGraph.nodes) {
                                self.newGraph.nodes = self.newGraph.nodes.filter(node => node.id !== d.id);
                            }
                            if (self.newGraph.links) {
                                self.newGraph.links = self.newGraph.links.filter(link => 
                                    (typeof link.source === 'object' ? link.source.id !== d.id : link.source !== d.id) && 
                                    (typeof link.target === 'object' ? link.target.id !== d.id : link.target !== d.id)
                                );
                            }
                        }
                        
                        // Update the oldGraph reference
                        self.oldGraph = graph;
                        
                        // Re-render with consistent parameters
                        self.renderGraph(
                            svg,
                            graph,
                            isEditable,
                            false,  // Don't reset layout after deletion
                            previewScale,
                            commonNodeIds,
                            true,   // Disable extension in main graph
                            false,  // Keep editing enabled
                            modifiedNodeIds
                        );
                        
                        // Hide context menu
                        contextMenu.style('display', 'none');
                    });
                
                // Add option to create edge - THIS WAS MISSING
                contextMenu.append('div')
                    .text('Create Edge From Here')
                    .on('click', () => {
                        self.logUserAction("Started edge creation");
                        // Store source node for edge creation
                        self.edgeCreationSource = d;
                        
                        // Add helper text
                        svg.append('text')
                            .attr('class', 'edge-creation-help')
                            .attr('x', 10)
                            .attr('y', 30)
                            .text('Click on another node to create edge')
                            .style('font-size', '14px')
                            .style('fill', '#4CAF50');
                        
                        // Highlight selected node
                        d3.select(this).select('circle')
                            .style('stroke', '#4CAF50')
                            .style('stroke-width', '3px');
                        
                        // Hide context menu
                        contextMenu.style('display', 'none');
                    });
                
                // Add click handler to hide menu when clicking elsewhere
                d3.select('body').on('click.context-menu', function() {
                    contextMenu.style('display', 'none');
                });
            });
            
            // Handle clicking on nodes for edge creation
            nodes.on('click', function(event, d) {
                if (self.edgeCreationSource && self.edgeCreationSource !== d) {
                    self.logUserAction("Created new edge");
                    // Create new edge
                    const newEdge = {
                        id: `edge-${self.edgeCreationSource.id}-${d.id}`,
                        source: self.edgeCreationSource,
                        target: d,
                        label: 'relation'
                    };
                    
                    // Add to graph data
                    graph.edges.push(newEdge);
                    
                    // Add to backend graph structure
                    if (self.newGraph && self.newGraph.links) {
                        self.newGraph.links.push({
                            source: self.edgeCreationSource.id,
                            target: d.id,
                            type: 'relation'
                        });
                    }
                    
                    // Update the oldGraph reference
                    self.oldGraph = graph;
                    
                    // Clear edge creation state
                    self.edgeCreationSource = null;
                    
                    // Remove helper text
                    svg.selectAll('.edge-creation-help').remove();
                    
                    // Remove highlighting from all nodes
                    svg.selectAll('.node circle')
                        .style('stroke', d => {
                            if (modifiedNodeIds && modifiedNodeIds.has(d.id)) {
                                return '#ffc107'; // Amber border for modified
                            }
                            return '#999'; // Default border
                        })
                        .style('stroke-width', d => {
                            if (modifiedNodeIds && modifiedNodeIds.has(d.id)) {
                                return '2.5px';
                            }
                            return '1.5px';
                        });
                    
                    // Re-render the graph without resetting layout
                    self.renderGraph(
                        svg,
                        graph,
                        isEditable,
                        false,  // Don't reset layout for edge addition
                        previewScale,
                        commonNodeIds,
                        true,   // Disable extension in main graph
                        false,  // Keep editing enabled
                        modifiedNodeIds
                    );
                }
            });
            
            // Add class property to track edge creation state if not already defined
            if (!self.hasOwnProperty('edgeCreationSource')) {
                self.edgeCreationSource = null;
            }
        }
    
        // Define tick function for updating positions
        function ticked() {
            // Update edge paths with proper error checking
            edgePaths.attr('d', function(d) {
                // Ensure source and target are objects with valid x,y coordinates
                if (!d.source || !d.source.x || !d.source.y || !d.target || !d.target.x || !d.target.y) {
                    return 'M0,0L0,0'; // Return a valid empty path if coordinates are invalid
                }
                
                // Calculate the path between source and target nodes
                return `M${d.source.x},${d.source.y}L${d.target.x},${d.target.y}`;
            });
            
            // Update edge labels with proper error checking
            edgeLabels.attr('transform', function(d) {
                // Ensure source and target are objects with valid x,y coordinates
                if (!d.source || !d.source.x || !d.source.y || !d.target || !d.target.x || !d.target.y) {
                    return 'translate(0,0)'; // Return a valid position if coordinates are invalid
                }
                
                // Position the edge label halfway between source and target
                const midX = (d.source.x + d.target.x) / 2;
                const midY = (d.source.y + d.target.y) / 2;
                return `translate(${midX},${midY})`;
            });
            
            // Update nodes with proper error checking
            nodes.attr('transform', function(d) {
                // Ensure node has valid x,y coordinates
                if (!d.x || !d.y) {
                    return 'translate(0,0)'; // Return a valid position if coordinates are invalid
                }
                
                return `translate(${d.x},${d.y})`;
            });
        }
    
        function dragstarted(event, d) {
            if (!isEditable) return;
            
            // Log node drag start
            self.logUserAction("Started dragging node");
            
            // Stop the simulation entirely when drag starts
            simulation.stop();
            
            // Store initial position
            d.fx = d.x;
            d.fy = d.y;
        }
    
        function dragged(event, d) {
            if (!isEditable) return;
            
            // Apply boundary constraints to keep nodes within the view area
            const padding = nodeHeight / 2 + 10; // Add some padding based on node height
            
            // Calculate bounded x and y coordinates
            const boundedX = Math.max(padding, Math.min(width - padding, event.x));
            const boundedY = Math.max(padding, Math.min(height - padding, event.y));
            
            // Update only the position of the dragged node
            d.x = boundedX;
            d.y = boundedY;
            d.fx = boundedX; // Fix position
            d.fy = boundedY; // Fix position
            
            // Manual update just for this node
            d3.select(this).attr("transform", `translate(${d.x},${d.y})`);
            
            // Update connected edges manually
            edgePaths.each(function(edge) {
                if ((edge.source === d) || (edge.target === d)) {
                    // Only update edges connected to this node
                    const sourceX = edge.source.x;
                    const sourceY = edge.source.y;
                    const targetX = edge.target.x;
                    const targetY = edge.target.y;
                    
                    // Calculate angle for arrow positioning
                    const dx = targetX - sourceX;
                    const dy = targetY - sourceY;
                    const angle = Math.atan2(dy, dx);
                    
                    // Adjust start/end points for rectangle nodes
                    let startX, startY, endX, endY;
    
                    // Calculate rectangle intersection points for source node
                    const sourceHalfWidth = nodeWidth / 2;
                    const sourceHalfHeight = nodeHeight / 2;
                    
                    if (Math.abs(dx) * sourceHalfHeight > Math.abs(dy) * sourceHalfWidth) {
                        // Intersects with left/right side
                        const sign = dx > 0 ? 1 : -1;
                        startX = sourceX + sign * sourceHalfWidth;
                        startY = sourceY + (dy / dx) * sign * sourceHalfWidth;
                    } else {
                        // Intersects with top/bottom side
                        const sign = dy > 0 ? 1 : -1;
                        startX = sourceX + (dx / dy) * sign * sourceHalfHeight;
                        startY = sourceY + sign * sourceHalfHeight;
                    }
                    
                    // Calculate rectangle intersection points for target node
                    const targetHalfWidth = nodeWidth / 2;
                    const targetHalfHeight = nodeHeight / 2;
                    
                    if (Math.abs(dx) * targetHalfHeight > Math.abs(dy) * targetHalfWidth) {
                        // Intersects with left/right side
                        const sign = dx > 0 ? -1 : 1;
                        endX = targetX + sign * targetHalfWidth;
                        endY = targetY + (dy / dx) * sign * targetHalfWidth;
                    } else {
                        // Intersects with top/bottom side
                        const sign = dy > 0 ? -1 : 1;
                        endX = targetX + (dx / dy) * sign * targetHalfHeight;
                        endY = targetY + sign * targetHalfHeight;
                    }
                    
                    // Update the path
                    d3.select(this).attr('d', `M${startX},${startY}L${endX},${endY}`);
                }
            });
            
            // Update edge labels connected to this node
            edgeLabels.each(function(edge) {
                if (edge.source === d || edge.target === d) {
                    const midX = (edge.source.x + edge.target.x) / 2;
                    const midY = (edge.source.y + edge.target.y) / 2;
                    d3.select(this).attr('transform', `translate(${midX},${midY})`);
                }
            });
        }
    
        function dragended(event, d) {
            if (!isEditable) return;
            
            // Log node drag end
            self.logUserAction("Finished dragging node");
            
            // Keep the node fixed at its new position
            d.fx = d.x;
            d.fy = d.y;
        }
    
        // Add button to add new nodes if editable
        if (isEditable && !disableEditing) {
            const addButton = svg.append("g")
                .attr("class", "add-node-button")
                .attr("transform", `translate(${width - 40}, ${height - 40})`)
                .style("cursor", "pointer");
            
            addButton.append("circle")
                .attr("r", 20)
                .attr("fill", "#4CAF50");
            
            addButton.append("text")
                .attr("text-anchor", "middle")
                .attr("dy", "0.3em")
                .attr("fill", "white")
                .attr("font-size", "24px")
                .text("+");
            
            addButton.on("click", function() {
                self.logUserAction("Adding new node");
                // Generate a unique ID
                let maxId = 0;
                graph.nodes.forEach(node => {
                    if (node.id && typeof node.id === 'string' && node.id.startsWith('Node')) {
                        const idNum = parseInt(node.id.replace('Node', ''), 10);
                        if (!isNaN(idNum) && idNum > maxId) {
                            maxId = idNum;
                        }
                    }
                });
                
                const newId = `Node${maxId + 1}`;
                const newNode = {
                    id: newId,
                    label: `Node ${newId}`,
                    x: width / 2,
                    y: height / 2
                };
                
                // Only add to the graph object once
                graph.nodes.push(newNode);
                
                // Redraw the graph with the new node
                self.renderGraph(svg, graph, isEditable, false, previewScale, 
                    commonNodeIds, disableExtension, disableEditing, modifiedNodeIds);
            });
        }
    
        // Run simulation with proper settings based on render type
        if (isInitialRender) {
            // For initial render, run the simulation with full strength
            simulation.alpha(0.5).restart();
        } else {
            // For updates, just run a few ticks to adjust positions
            for (let i = 0; i < 10; i++) simulation.tick();
            ticked();
            simulation.stop();
        }

        // Add this after the edgePaths creation code
        if (isEditable && !disableEditing) {
            // Create a wider transparent path for better edge selection
            svg.selectAll('.edge-hitbox')
                .data(graph.edges)
                .enter()
                .append('path')
                .attr('class', 'edge-hitbox')
                .style('stroke', 'transparent')
                .style('stroke-width', '15px') // Much wider for easier selection
                .style('fill', 'none')
                .style('cursor', 'pointer')
                .on('contextmenu', function(event, d) {
                    // Prevent default right-click menu
                    event.preventDefault();
                    
                    // Show context menu for edge
                    const contextMenu = document.querySelector('.context-menu');
                    contextMenu.innerHTML = '';
                    contextMenu.style.display = 'block';
                    contextMenu.style.left = `${event.pageX}px`;
                    contextMenu.style.top = `${event.pageY}px`;
                    
                    // Add option to edit edge label
                    const editOption = document.createElement('div');
                    editOption.textContent = 'Edit Label';
                    editOption.onclick = function() {
                        const newLabel = prompt('Enter new edge label:', d.label || '');
                        if (newLabel !== null) {
                            d.label = newLabel;
                            svg.selectAll('.edge-label text').filter(ed => ed === d)
                                .text(newLabel);
                        }
                        contextMenu.style.display = 'none';
                    };
                    contextMenu.appendChild(editOption);
                    
                    // Add option to delete edge
                    const deleteOption = document.createElement('div');
                    deleteOption.textContent = 'Delete Edge';
                    deleteOption.onclick = function() {
                        self.logUserAction("Deleted edge");
                        // Find the edge index and remove it from the graph
                        const edgeIndex = graph.edges.findIndex(e => 
                            e.source.id === d.source.id && e.target.id === d.target.id);
                        if (edgeIndex !== -1) {
                            graph.edges.splice(edgeIndex, 1);
                            // Re-render the graph
                            self.renderGraph(svg, graph, isEditable, false, previewScale, 
                                commonNodeIds, disableExtension, disableEditing, modifiedNodeIds);
                        }
                        contextMenu.style.display = 'none';
                    };
                    contextMenu.appendChild(deleteOption);
                })
                .on('click', function(event, d) {
                    // Allow direct click on edge to edit label
                    const newLabel = prompt('Enter new edge label:', d.label || '');
                    if (newLabel !== null) {
                        d.label = newLabel;
                        svg.selectAll('.edge-label text').filter(ed => ed === d)
                            .text(newLabel);
                    }
                });
                
            // Update the tick function to include hitbox paths
            const originalTicked = ticked;
            ticked = function() {
                originalTicked();
                svg.selectAll('.edge-hitbox')
                    .attr('d', d => {
                        const sourceX = d.source.x;
                        const sourceY = d.source.y;
                        const targetX = d.target.x;
                        const targetY = d.target.y;
                        return `M${sourceX},${sourceY}L${targetX},${targetY}`;
                    });
            };
        }

        // Add this inside the renderGraph method, after the edgeLabels creation code
        // and before the final ticked() function

        // // Add edge label editing functionality
        // if (isEditable && !disableEditing) {
        //     // Add double-click handler for edge labels
        //     edgeLabels.selectAll('text').on('dblclick', function(event, d) {
        //         event.preventDefault();
        //         event.stopPropagation();
                
        //         // Calculate position for the text input
        //         const [x, y] = d3.pointer(event, svg.node());
                
        //         // Get current text
        //         const currentText = d.label || d.type || '';
                
        //         // Create input element for editing
        //         const foreignObject = svg.append('foreignObject')
        //             .attr('x', x - 60)
        //             .attr('y', y - 15)
        //             .attr('width', 120)
        //             .attr('height', 30);
                    
        //         const input = foreignObject.append('xhtml:input')
        //             .attr('type', 'text')
        //             .attr('value', currentText)
        //             .style('width', '100%')
        //             .style('height', '100%')
        //             .style('padding', '2px')
        //             .style('font-size', fontSize + 'px')
        //             .style('border', '1px solid #999')
        //             .style('border-radius', '3px');
                
        //         // Focus on the input
        //         setTimeout(() => {
        //             input.node().focus();
        //             input.node().select();
        //         }, 10);
                
        //         // Handle input blur (save changes)
        //         input.on('blur', function() {
        //             const newText = this.value.trim();
        //             d.label = newText;  // Update edge label
        //             d.type = newText;   // Update type for consistency
        //             d3.select(event.currentTarget.parentNode).select('text').text(newText); // Update visible text
        //             foreignObject.remove(); // Remove input
        //         });
                
        //         // Handle keypress events
        //         input.on('keydown', function(e) {
        //             if (e.key === 'Enter') {
        //                 const newText = this.value.trim();
        //                 d.label = newText;  // Update edge label
        //                 d.type = newText;   // Update type for consistency
        //                 d3.select(event.currentTarget.parentNode).select('text').text(newText); // Update visible text
        //                 foreignObject.remove(); // Remove input
        //             } else if (e.key === 'Escape') {
        //                 foreignObject.remove(); // Remove input without saving
        //             }
        //             e.stopPropagation(); // Prevent other handlers from firing
        //         });
                
        //         input.on('click', function(e) {
        //             e.stopPropagation(); // Prevent svg click from removing the input
        //         });
        //     });
        // }

        // Add edge label editing functionality
        if (isEditable && !disableEditing) {
            edgeLabels.select('text').on('dblclick', function(event, d) {
                // Prevent event bubbling
                event.preventDefault();
                event.stopPropagation();

                // Get the current position and text
                const currentLabel = d.label || d.type || '';
                const bbox = this.getBoundingClientRect();
                const svgRect = svg.node().getBoundingClientRect();
                
                // Create an input field for editing
                const foreignObject = svg.append('foreignObject')
                    .attr('x', bbox.x - svgRect.x - 50) // Center the input field
                    .attr('y', bbox.y - svgRect.y - 15) // Position slightly above
                    .attr('width', 100)
                    .attr('height', 30)
                    .style('overflow', 'visible')
                    .attr('class', 'edge-editor');
                
                const input = foreignObject.append('xhtml:input')
                    .attr('type', 'text')
                    .attr('value', currentLabel)
                    .style('width', '100%')
                    .style('height', '100%')
                    .style('font-size', fontSize + 'px')
                    .style('border', '1px solid #3498db')
                    .style('border-radius', '4px')
                    .style('padding', '2px 4px')
                    .style('text-align', 'center');
                
                // Focus the input field
                input.node().focus();
                input.node().select();
                
                // Handle Enter key press
                input.on('keypress', function(event) {
                    if (event.key === 'Enter') {
                        event.preventDefault();
                        this.blur();
                    }
                });
                
                // Handle blur event
                input.on('blur', function() {
                    self.logUserAction("Changed edge label");
                    // Update the edge label
                    const newLabel = this.value.trim();
                    d.label = newLabel;
                    d.type = newLabel; // Update both properties to ensure consistency
                    
                    // Update the label text
                    d3.select(edgeLabels.nodes()[graph.edges.indexOf(d)])
                      .select('text')
                      .text(newLabel);
                    
                    // Remove the input field
                    foreignObject.remove();
                    
                    // Trigger a simulation tick to update positions
                    simulation.alpha(0.1).restart();
                });
            });
        }
    }
    
    updateCurrentGraph(graph) {
        if (graph) {
            // Convert from backend format (with "links") to the format used by renderGraph (with "edges")
            this.currentGraph = {
                nodes: graph.nodes ? graph.nodes.map(node => ({
                    id: node.id,
                    label: node.description || node.label || node.id, // Use description as label
                    // Clear previous positions for fresh layout
                    x: undefined,
                    y: undefined,
                    fx: null,
                    fy: null
                })) : [],
                edges: []  // Start with empty edges array, we'll populate it correctly below
            };
            
            // Create a node map for reference
            const nodeMap = {};
            this.currentGraph.nodes.forEach(node => {
                nodeMap[node.id] = node;
            });
            
            // Process edges with proper object references
            const sourceEdges = graph.links || graph.edges || [];
            this.currentGraph.edges = sourceEdges.map(edge => {
                // Get source and target node objects
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                
                // Make sure we have valid references to node objects, not just IDs
                const sourceNode = nodeMap[sourceId];
                const targetNode = nodeMap[targetId];
                
                // Only create edges between valid nodes
                if (sourceNode && targetNode) {
                    return {
                        id: `edge-${sourceId}-${targetId}`,
                        source: sourceNode,  // Use the actual node object
                        target: targetNode,  // Use the actual node object
                        label: edge.type || edge.label || ''
                    };
                }
                return null;
            }).filter(edge => edge !== null); // Remove any invalid edges
            
            // Always use initialRender=true for consistent layout
            this.renderGraph(this.currentGraphSvg, this.currentGraph, true, true);
        } else {
            // Handle case when graph is null or undefined
            console.warn("Received null or undefined graph");
            this.currentGraph = this.generateRandomGraph();
            this.renderGraph(this.currentGraphSvg, this.currentGraph, true, true);
        }
    }
    
    saveVersion() {
        if (this.currentGraph && this.newGraph) {
            const version = {
                number: ++this.currentVersion,
                timestamp: Date.now(),
                simGraph: JSON.parse(JSON.stringify(this.currentGraph)),
                newGraph: JSON.parse(JSON.stringify(this.newGraph))
            };
            
            this.versionHistory.push(version);
            return version;
        }
        return null;
    }
    
    loadVersion(versionNumber) {
        const version = this.versionHistory.find(v => v.number === versionNumber);
        if (version) {
            // Find common nodes for highlighting
            const commonNodeIds = this.findCommonNodes(version.simGraph, version.newGraph);
            
            // Load and render both graphs
            this.renderGraph(
                this.oldGraphSvg, 
                version.newGraph, 
                true, 
                false, 
                1, 
                commonNodeIds
            );
            
            this.renderGraph(
                this.currentGraphSvg, 
                version.simGraph, 
                true
            );
            
            // Update current graph references
            this.currentGraph = version.simGraph;
            this.newGraph = version.newGraph;
        }
    }
    
    getVersions() {
        return this.versionHistory;
    }
    
    clearVersions() {
        this.versionHistory = [];
        this.currentVersion = 0;
    }
    
    confirmCurrentGraph() {
        if (!this.currentGraph) return null;
        
        this.oldGraph = {
            nodes: JSON.parse(JSON.stringify(this.currentGraph.nodes)),
            edges: this.currentGraph.edges.map(edge => ({
                ...edge,
                source: typeof edge.source === 'object' ? edge.source.id : edge.source,
                target: typeof edge.target === 'object' ? edge.target.id : edge.target
            }))
        };
        
        // Save to history
        const graphState = {
            timestamp: Date.now(),
            graph: this.oldGraph
        };
        
        this.graphHistory.push(graphState);
        localStorage.setItem('graphHistory', JSON.stringify(this.graphHistory));
        
        // Clear current graph area
        this.currentGraph = null;
        this.currentGraphSvg.selectAll("*").remove();
        
        // Clear version history
        this.clearVersions();
        
        return this.oldGraph;
    }
    
    // Rename the old save method to downloadHistory
    downloadHistory() {
        if (this.graphHistory.length > 0) {
            const historyBlob = new Blob(
                [JSON.stringify(this.graphHistory, null, 2)], 
                { type: 'application/json' }
            );
            const url = URL.createObjectURL(historyBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `graph_history_${new Date().toISOString().slice(0,10)}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }
    }

    // Add a method to find common nodes
    findCommonNodes(graph1, graph2) {
        if (!graph1 || !graph2 || !graph1.nodes || !graph2.nodes) {
            return new Set();
        }
        
        const graph1NodeIds = new Set(graph1.nodes.map(n => n.id));
        const commonNodeIds = new Set();
        
        graph2.nodes.forEach(node => {
            if (graph1NodeIds.has(node.id)) {
                commonNodeIds.add(node.id);
            }
        });
        
        return commonNodeIds;
    }

    // Add this method to GraphManager class
    getMaxNodeId(graph) {
        if (!graph || !graph.nodes || graph.nodes.length === 0) {
            return 0;
        }
        
        let maxId = 0;
        graph.nodes.forEach(node => {
            // Extract numeric part if ID is in format "Node123"
            const match = node.id.match(/Node(\d+)/);
            if (match && match[1]) {
                const numericId = parseInt(match[1], 10);
                maxId = Math.max(maxId, numericId);
            } else {
                // If ID is just a number
                const numericId = parseInt(node.id, 10);
                if (!isNaN(numericId)) {
                    maxId = Math.max(maxId, numericId);
                }
            }
        });
        
        return maxId;
    }

    // Generate a new unique node ID
    generateNewNodeId(graph) {
        const maxId = this.getMaxNodeId(graph);
        return `Node${maxId + 1}`;
    }

    // Update the optimizeGraphLayout method for top-to-bottom layout

    optimizeGraphLayout(graph, width, height) {
        // Step 1: Create a layered structure by analyzing graph connections
        const nodeMap = {};
        graph.nodes.forEach(node => {
            nodeMap[node.id] = {
                node: node,
                outgoing: [],
                incoming: [],
                visited: false,
                layer: -1
            };
        });
        
        // Build connectivity information
        graph.edges.forEach(edge => {
            const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
            const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
            
            if (nodeMap[sourceId] && nodeMap[targetId]) {
                nodeMap[sourceId].outgoing.push(targetId);
                nodeMap[targetId].incoming.push(sourceId);
            }
        });
        
        // Find roots (nodes with no incoming edges)
        const roots = Object.values(nodeMap)
            .filter(info => info.incoming.length === 0)
            .map(info => info.node.id);
        
        // If no roots found, use nodes with the most outgoing edges
        if (roots.length === 0) {
            const maxOutgoing = Math.max(...Object.values(nodeMap).map(n => n.outgoing.length));
            Object.values(nodeMap)
                .filter(n => n.outgoing.length === maxOutgoing)
                .forEach(n => roots.push(n.node.id));
        }
        
        // Assign layers using BFS (top to bottom)
        let currentLayer = 0;
        let currentNodes = [...roots];
        
        while (currentNodes.length > 0) {
            const nextLayer = [];
            
            currentNodes.forEach(nodeId => {
                if (nodeMap[nodeId].layer === -1) {
                    nodeMap[nodeId].layer = currentLayer;
                    nodeMap[nodeId].visited = true;
                    
                    // Add unvisited children to next layer
                    nodeMap[nodeId].outgoing.forEach(childId => {
                        if (!nodeMap[childId].visited && !nextLayer.includes(childId)) {
                            nextLayer.push(childId);
                        }
                    });
                }
            });
            
            currentNodes = nextLayer;
            currentLayer++;
        }
        
        // Handle any unvisited nodes (due to cycles)
        Object.values(nodeMap).forEach(info => {
            if (info.layer === -1) {
                info.layer = currentLayer;
            }
        });
        
        // Count nodes per layer
        const layerCounts = {};
        Object.values(nodeMap).forEach(info => {
            layerCounts[info.layer] = (layerCounts[info.layer] || 0) + 1;
        });
        
        const maxLayer = Math.max(...Object.keys(layerCounts).map(Number));
        
        // Group nodes by layer
        const layerNodes = {};
        Object.values(nodeMap).forEach(info => {
            if (!layerNodes[info.layer]) {
                layerNodes[info.layer] = [];
            }
            layerNodes[info.layer].push(info);
        });
        
        // Position each node within its layer
        // Increased top padding to move nodes down from modify area
        const topPadding = 140; // More space at the top to avoid the modify input area
        const sidePadding = 70;  // Increased from 50
        const bottomPadding = 50; // Padding from bottom
        
        // Calculate available space
        const availableWidth = width - (sidePadding * 2);
        const availableHeight = height - topPadding - bottomPadding;
        
        // Calculate layer count for better vertical distribution
        const layerCount = maxLayer + 1;
        
        // Ensure we're using enough vertical space
        const verticalSpacing = layerCount <= 1 ? 
            availableHeight / 2 : // If only one layer, put it in the middle
            availableHeight / (layerCount <= 3 ? 4 : layerCount); // More space for fewer layers
        
        // Process each layer
        for (let layer = 0; layer <= maxLayer; layer++) {
            if (!layerNodes[layer]) continue;
            
            // Calculate y position based on layer (top to bottom)
            const yPosition = topPadding + (layer * verticalSpacing);
            
            // Get nodes in this layer and limit horizontal spread
            const nodesInLayer = layerNodes[layer].length;
            
            // Limit the maximum width used based on node count
            // This prevents excessive horizontal spread while ensuring adequate spacing
            const usedWidth = Math.min(
                availableWidth,
                nodesInLayer * 200 // Increased from 150 to 200px per node
            );
            
            // Calculate horizontal step size with wider spacing
            let xStep = nodesInLayer > 1 ? usedWidth / (nodesInLayer - 1) : usedWidth / 2;
            
            // Set a minimum step size to prevent nodes from being too close
            xStep = Math.max(xStep, 200); // Increased from 180px
            
            // Limit maximum step size for very sparse graphs
            xStep = Math.min(xStep, 300); // Increased from 250px
            
            // Calculate total width needed
            const totalWidth = (nodesInLayer - 1) * xStep;
            
            // Calculate starting X position to center the nodes
            const startX = sidePadding + (availableWidth - totalWidth) / 2;
            
            // Position nodes horizontally within the layer
            layerNodes[layer].forEach((info, index) => {
                // Position horizontally with improved spread
                const xPosition = nodesInLayer > 1 
                    ? startX + (index * xStep)
                    : width / 2; // Center if only one node
                
                info.node.x = xPosition;
                info.node.y = yPosition;
                
                // Fix position to prevent force layout from moving it
                info.node.fx = xPosition;
                info.node.fy = yPosition;
            });
        }
        
        return graph;
    }

    // Add this new method for extension preview layout
    optimizeExtensionLayout(graph, width, height) {
        // Start with a copy of the graph to avoid modifying the original
        const graphCopy = JSON.parse(JSON.stringify(graph));
        
        // Step 1: Create a layered structure by analyzing graph connections
        const nodeMap = {};
        graphCopy.nodes.forEach(node => {
            nodeMap[node.id] = {
                node: node,
                outgoing: [],
                incoming: [],
                visited: false,
                layer: -1
            };
        });
        
        // Build connectivity information
        graphCopy.edges.forEach(edge => {
            const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
            const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
            
            if (nodeMap[sourceId] && nodeMap[targetId]) {
                nodeMap[sourceId].outgoing.push(targetId);
                nodeMap[targetId].incoming.push(sourceId);
            }
        });
        
        // Find roots (nodes with no incoming edges)
        const roots = Object.values(nodeMap)
            .filter(info => info.incoming.length === 0)
            .map(info => info.node.id);
        
        // If no roots found, use nodes with the most outgoing edges
        if (roots.length === 0) {
            const maxOutgoing = Math.max(...Object.values(nodeMap).map(n => n.outgoing.length));
            Object.values(nodeMap)
                .filter(n => n.outgoing.length === maxOutgoing)
                .forEach(n => roots.push(n.node.id));
        }
        
        // Assign layers using BFS (top to bottom)
        let currentLayer = 0;
        let currentNodes = [...roots];
        
        while (currentNodes.length > 0) {
            const nextLayer = [];
            
            currentNodes.forEach(nodeId => {
                if (nodeMap[nodeId].layer === -1) {
                    nodeMap[nodeId].layer = currentLayer;
                    nodeMap[nodeId].visited = true;
                    
                    // Add unvisited children to next layer
                    nodeMap[nodeId].outgoing.forEach(childId => {
                        if (!nodeMap[childId].visited && !nextLayer.includes(childId)) {
                            nextLayer.push(childId);
                        }
                    });
                }
            });
            
            currentNodes = nextLayer;
            currentLayer++;
        }
        
        // Handle any unvisited nodes (due to cycles)
        Object.values(nodeMap).forEach(info => {
            if (info.layer === -1) {
                info.layer = currentLayer;
            }
        });
        
        // Count nodes per layer
        const layerCounts = {};
        Object.values(nodeMap).forEach(info => {
            layerCounts[info.layer] = (layerCounts[info.layer] || 0) + 1;
        });
        
        const maxLayer = Math.max(...Object.keys(layerCounts).map(Number));
        
        // Group nodes by layer
        const layerNodes = {};
        Object.values(nodeMap).forEach(info => {
            if (!layerNodes[info.layer]) {
                layerNodes[info.layer] = [];
            }
            layerNodes[info.layer].push(info);
        });
        
        // Position each node within its layer
        const topPadding = 100;  // Reduced from 160
        const sidePadding = 80;  // Reduced from 160
        const bottomPadding = 80; // Reduced from 160
        
        // Calculate available space
        const availableWidth = width - (sidePadding * 2);
        const availableHeight = height - topPadding - bottomPadding;
        
        // Calculate layer count for better vertical distribution
        const layerCount = maxLayer + 1;
        
        // MODERATE VERTICAL SPACING - Reduced the multiplier
        const verticalSpacing = layerCount <= 1 ? 
            availableHeight / 2 : 
            (availableHeight / (layerCount <= 3 ? 3 : layerCount)) * 2; // Reduced multiplier from 4 to 2
        
        // Process each layer
        for (let layer = 0; layer <= maxLayer; layer++) {
            if (!layerNodes[layer]) continue;
            
            // Calculate y position based on layer (top to bottom)
            const yPosition = topPadding + (layer * verticalSpacing);
            
            // Get nodes in this layer with reasonable horizontal spacing
            const nodesInLayer = layerNodes[layer].length;
            
            // Limit the maximum width used based on node count
            const usedWidth = Math.min(
                availableWidth,
                nodesInLayer * 200 // Reduced from 400px to 200px per node
            );
            
            // Calculate horizontal step size with more reasonable spacing
            let xStep = nodesInLayer > 1 ? usedWidth / (nodesInLayer - 1) : usedWidth / 2;
            
            // Set a minimum step size to prevent nodes from being too close
            xStep = Math.max(xStep, 180); // Reduced from 350px to 180px
            
            // Limit maximum step size for very sparse graphs
            xStep = Math.min(xStep, 300); // Reduced from 500px to 300px
            
            // Calculate total width needed
            const totalWidth = (nodesInLayer - 1) * xStep;
            
            // Calculate starting X position to center the nodes
            const startX = sidePadding + (availableWidth - totalWidth) / 2;
            
            // Position nodes horizontally within the layer
            layerNodes[layer].forEach((info, index) => {
                // Position horizontally with improved spread
                const xPosition = nodesInLayer > 1 
                    ? startX + (index * xStep)
                    : width / 2; // Center if only one node
                
                info.node.x = xPosition;
                info.node.y = yPosition;
                
                // Fix position to prevent force layout from moving it
                info.node.fx = xPosition;
                info.node.fy = yPosition;
            });
        }
        
        return graphCopy;
    }
}