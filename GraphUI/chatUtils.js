class ChatManager {
    constructor() {
        this.chatArea = document.getElementById('chatArea');
        this.messages = [];
        this.graphPreview = null;
        this.graphManager = new GraphManager();
        this.initGraphPreview();
        this.isPreviewVisible = false;
        
        // Configure marked.js globally with better options
        marked.setOptions({
            highlight: function(code, language) {
                if (Prism.languages[language]) {
                    return Prism.highlight(code, Prism.languages[language], language);
                }
                return code;
            },
            breaks: true,
            gfm: true,
            headerIds: true,
            pedantic: false,
            sanitize: false,
            smartLists: true,
            xhtml: false
        });
    }

    initGraphPreview() {
        // 创建预览窗口
        this.graphPreview = document.createElement('div');
        this.graphPreview.className = 'graph-preview';
        
        // 创建SVG容器
        const svg = d3.select(this.graphPreview)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%');
            
        document.body.appendChild(this.graphPreview);
    }

    addMessage(text, sender, graphData = null) {
        const message = {
            id: Date.now(),
            text,
            sender,
            timestamp: new Date(),
            graphData
        };
        this.messages.push(message);
        
        // Create message container
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.style.maxHeight = 'none'; // Ensure no height restriction
        messageDiv.style.overflow = 'visible'; // Make sure overflow content is visible
        
        // Add avatar
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        messageDiv.appendChild(avatarDiv);
        
        // Add content container
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.style.maxHeight = 'none'; // Ensure no height restriction
        contentDiv.style.overflow = 'visible'; // Make sure overflow content is visible
        messageDiv.appendChild(contentDiv);
        
        // Add sender label
        const senderDiv = document.createElement('div');
        senderDiv.style.fontWeight = 'bold';
        senderDiv.textContent = sender === 'user' ? 'User:' : 'AI:';
        contentDiv.appendChild(senderDiv);

        console.log('sender:', sender);
        
        // Create markdown content container
        if (text) {
            // Enhanced rendering for AI responses - special handling for code blocks
            if (sender === 'ai') {
                // Pre-process the text to ensure proper code block formatting
                let processedText = text;
                
                // Create container for marked content
                const markdownDiv = document.createElement('div');
                markdownDiv.className = 'markdown-content';
                markdownDiv.style.maxHeight = 'none'; // Ensure no height restriction
                markdownDiv.style.overflow = 'visible'; // Make sure overflow content is visible
                
                // Parse markdown with marked
                markdownDiv.innerHTML = marked.parse(processedText);
                
                // Post-process code blocks for better display
                const codeBlocks = markdownDiv.querySelectorAll('pre code');
                codeBlocks.forEach(block => {
                    // Find language class
                    const classes = block.className.split(' ');
                    const langClass = classes.find(cls => cls.startsWith('language-'));
                    const language = langClass ? langClass.replace('language-', '') : '';

                    const codeStr = block.textContent;
                    console.log('codeStr:', codeStr, Prism, window.Prism);
                    const codeHtml = window.Prism.highlight(codeStr, Prism.languages.python, 'python');
                    block.innerHTML = codeHtml;
                    
                    // Style the code block container
                    const preBlock = block.parentElement;
                    if (preBlock && language) {
                        preBlock.setAttribute('data-language', language);
                        preBlock.style.position = 'relative';
                        preBlock.className = 'language-python';
                        preBlock.style.maxHeight = 'none'; // Ensure no height restriction
                        preBlock.style.overflow = 'visible'; // Make sure overflow content is visible
                        
                        // Add language label
                        const langLabel = document.createElement('span');
                        langLabel.className = 'language-label';
                        langLabel.textContent = language;
                        langLabel.style.position = 'absolute';
                        langLabel.style.top = '0';
                        langLabel.style.right = '10px';
                        langLabel.style.fontSize = '12px';
                        langLabel.style.padding = '2px 6px';
                        langLabel.style.background = '#272822';
                        langLabel.style.borderRadius = '0 0 4px 4px';
                        langLabel.style.color = '#ddd';
                        preBlock.appendChild(langLabel);
                    }
                });
                console.log('markdownDiv:', markdownDiv.outerHTML);
                
                contentDiv.appendChild(markdownDiv);
            } else {
                // Simple rendering for user messages
                const textDiv = document.createElement('div');
                textDiv.textContent = text;
                textDiv.style.maxHeight = 'none'; // Ensure no height restriction
                textDiv.style.overflow = 'visible'; // Make sure overflow content is visible
                contentDiv.appendChild(textDiv);
            }
        }
        
        // Ensure the chat container can accommodate all content
        this.chatArea.style.maxHeight = 'none';
        this.chatArea.style.overflow = 'auto';
        
        this.chatArea.appendChild(messageDiv);
        
        // Scroll to bottom
        this.chatArea.scrollTop = this.chatArea.scrollHeight;
        
        // Add graph preview functionality
        if (sender === 'ai' && graphData) {
            avatarDiv.addEventListener('mouseenter', (e) => {
                this.showGraphPreview(e, graphData);
            });
            
            avatarDiv.addEventListener('mouseleave', () => {
                this.hideGraphPreview();
            });
        }
    }

    showGraphPreview(event, graphData) {
        const preview = this.graphPreview;
        
        // 设置预览窗口大小
        const scale = 0.4;
        const previewWidth = 400;
        const previewHeight = 300;
        
        // 更新预览窗口大小和样式
        preview.style.width = `${previewWidth}px`;
        preview.style.height = `${previewHeight}px`;
        preview.innerHTML = '';
        
        // 创建SVG容器
        const svg = d3.select(preview)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%');
        
        // 使用传入的 graphData 创建图形
        const graph = {
            nodes: graphData.nodes.map(node => ({
                id: node.id,
                label: node.description
            })),
            edges: graphData.links.map(link => ({
                source: link.source,
                target: link.target,
                label: link.type
            }))
        };
    
        // 创建力导向布局
        const simulation = d3.forceSimulation(graph.nodes)
            .force("link", d3.forceLink(graph.edges).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(previewWidth / 2, previewHeight / 2));
    
        // 创建连线
        const links = svg.append("g")
            .selectAll("line")
            .data(graph.edges)
            .enter()
            .append("line")
            .style("stroke", "#999")
            .style("stroke-width", 1);
    
        // 创建节点
        const nodes = svg.append("g")
            .selectAll("g")
            .data(graph.nodes)
            .enter()
            .append("g");
    
        nodes.append("circle")
            .attr("r", 20)
            .style("fill", "#69b3a2");
    
        nodes.append("text")
            .text(d => d.label)
            .attr('text-anchor', 'middle')
            .attr('dy', '.35em')
            .style('font-size', '12px');
    
        // 更新力导向布局
        simulation.on("tick", () => {
            links
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
    
            nodes.attr("transform", d => `translate(${d.x},${d.y})`);
        });
    
        // 计算预览窗口位置
        let left = event.pageX + 20;
        let top = event.pageY - previewHeight / 2;
        
        // 确保预览窗口在视口内
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        if (left + previewWidth > viewportWidth) {
            left = event.pageX - previewWidth - 20;
        }
        if (top + previewHeight > viewportHeight) {
            top = viewportHeight - previewHeight - 20;
        }
        if (top < 20) {
            top = 20;
        }
        
        preview.style.display = 'block';
        preview.style.left = `${left}px`;
        preview.style.top = `${top}px`;
    }

    hideGraphPreview() {
        this.graphPreview.style.display = 'none';
        this.isPreviewVisible = false;
    }

    getLastUserMessage() {
        const userMessages = this.messages.filter(m => m.sender === 'user');
        return userMessages[userMessages.length - 1];
    }
}