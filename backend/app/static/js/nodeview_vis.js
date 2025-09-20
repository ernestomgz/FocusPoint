// Generic vis-network DAG mount (not used if page provides its own inline script)
window.FocusPointGraph = (function () {
  function mount(container, data, opts = {}) {
    const nodes = new vis.DataSet((data.nodes || []).map(n => ({
      ...n,
      shape: 'box',
      borderWidth: 3,
      color: {
        background: '#ffffff',
        border: (n.border || '#cccccc'),
        highlight: {background:'#ffffff', border:'#7c4dff'}
      },
      font: { color:'#111', size:12, face:'Inter, system-ui, sans-serif', multi:true },
      margin: 10
    })));

    const edges = new vis.DataSet((data.edges || []).map(e => ({
      ...e,
      arrows: { to: {enabled: true, type: 'vee', scaleFactor: 1.6} },
      width: 4,
      color: { color:'#2f1bb3', highlight:'#7c4dff', hover:'#7c4dff' },
      smooth: { type: 'cubicBezier' }
    })));

    const network = new vis.Network(container, { nodes, edges }, {
      layout: { hierarchical: { enabled: true, direction: 'LR', levelSeparation: 160, nodeSpacing: 120 } },
      physics: false,
      interaction: { hover: true, tooltipDelay: 80, zoomView: true, dragView: true }
    });

    return { network, nodes, edges };
  }
  return { mount };
})();

