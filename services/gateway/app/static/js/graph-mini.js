/** Компактный vis-network рендерер для чата и других панелей */
(function (global) {
  const LABEL_LAYER = {
    Material: "L1", Process: "L1", Equipment: "L1", ChemicalReagent: "L1", StandardMetric: "L1",
    Expert: "L2", Organization: "L2", Location: "L2", Timeline: "L2", Event: "L2", Facility: "L2", Document: "L2",
    TextParagraph: "L3", TextSection: "L3", LangContext: "L3", HeadingContext: "L3", DocumentText: "L3",
    ExperimentRun: "L4", TechStage: "L4", Measurement: "L4", Deviation: "L4", TrendVector: "L4",
    Formula: "L4", EnvironmentalCondition: "L4", Effect: "L4", Claim: "L4",
    SecurityRole: "L5", VerificationStatus: "L5", AuditTrail: "L5",
    TechnologySolution: "L6", EconomicIndicator: "L6", EnvironmentalIndicator: "L6",
  };

  const LAYER_COLOR = {
    L1: "#0288d1", L2: "#7b1fa2", L3: "#546e7a", L4: "#ef6c00", L5: "#c62828", L6: "#2e7d32", "L?": "#78909c",
  };

  const instances = new WeakMap();

  function layerOf(label) {
    return LABEL_LAYER[label] || "L?";
  }

  function shortLabel(node) {
    const props = node.props || {};
    const text = props.name || props.quote || props.raw_text_ru || props.title || node.label || node.id || "";
    const s = String(text).replace(/\s+/g, " ").trim();
    if (s.length > 18) return s.slice(0, 16) + "…";
    return s || String(node.id || "").slice(-12);
  }

  function relEndpoints(r) {
    return { from: r.from || r.from_, to: r.to };
  }

  function buildVisItems(nodes, rels, { animate = false } = {}) {
    const visNodes = nodes.map((n, i) => {
      const isSeed = !!(n.props && n.props._seed);
      const layer = layerOf(n.label);
      return {
        id: n.id,
        label: shortLabel(n),
        title: `${n.label}: ${n.id}`,
        color: {
          background: isSeed ? "#0071e3" : (LAYER_COLOR[layer] || LAYER_COLOR["L?"]),
          border: isSeed ? "#004999" : "#fff",
          highlight: { background: "#01579b", border: "#fff" },
        },
        font: { color: "#fff", size: 9, face: "Inter, sans-serif" },
        shape: "box",
        margin: 4,
        widthConstraint: { maximum: 88 },
        level: isSeed ? 0 : 1,
        hidden: animate,
        opacity: animate ? 0 : 1,
      };
    });
    const visEdges = rels.slice(0, 120).map((r, i) => {
      const { from, to } = relEndpoints(r);
      return {
        id: `e${i}`,
        from,
        to,
        title: r.type,
        arrows: { to: { enabled: true, scaleFactor: 0.4 } },
        color: { color: "rgba(144,202,249,0.75)", highlight: "#0288d1" },
        width: 0.8,
        smooth: { type: "dynamic", roundness: 0.35 },
        hidden: animate,
      };
    });
    return { visNodes, visEdges };
  }

  function destroy(container) {
    const inst = instances.get(container);
    if (inst?.network) {
      inst.network.destroy();
    }
    instances.delete(container);
    if (container) container.innerHTML = "";
  }

  function renderMiniGraph(container, graph, opts = {}) {
    if (!container) return null;
    destroy(container);
    const nodes = graph?.nodes || [];
    const rels = graph?.relationships || [];
    if (!nodes.length) return null;
    if (typeof vis === "undefined") {
      container.innerHTML = '<p class="muted small">vis-network не загружен</p>';
      return null;
    }

    const animate = opts.animate !== false;
    const { visNodes, visEdges } = buildVisItems(nodes, rels, { animate });
    const dataSets = {
      nodes: new vis.DataSet(visNodes),
      edges: new vis.DataSet(visEdges),
    };
    const network = new vis.Network(
      container,
      dataSets,
      {
        physics: {
          enabled: true,
          stabilization: { iterations: 40, fit: true },
          barnesHut: {
            gravitationalConstant: -800,
            centralGravity: 0.12,
            springLength: 120,
            springConstant: 0.02,
            damping: 0.25,
          },
        },
        interaction: { hover: true, zoomView: true, dragView: true, dragNodes: true },
      },
    );

    const reveal = () => {
      const nodeUpdates = dataSets.nodes.get().map((n, idx) => ({
        id: n.id,
        hidden: false,
        opacity: 1,
        delay: idx * 60,
      }));
      nodeUpdates.forEach((u, idx) => {
        setTimeout(() => dataSets.nodes.update({ id: u.id, hidden: false, opacity: 1 }), idx * 80);
      });
      rels.slice(0, 120).forEach((_, idx) => {
        setTimeout(() => {
          const eid = `e${idx}`;
          if (dataSets.edges.get(eid)) dataSets.edges.update({ id: eid, hidden: false });
        }, nodes.length * 80 + idx * 50);
      });
    };

    network.once("stabilizationIterationsDone", () => {
      network.fit({ animation: { duration: 350, easingFunction: "easeInOutQuad" } });
      setTimeout(() => network.setOptions({ physics: { enabled: false } }), 400);
    });

    if (animate) {
      setTimeout(reveal, 120);
    } else {
      dataSets.nodes.update(visNodes.map((n) => ({ id: n.id, hidden: false, opacity: 1 })));
      dataSets.edges.update(visEdges.map((e) => ({ id: e.id, hidden: false })));
    }

    instances.set(container, { network, dataSets });
    return network;
  }

  global.MKGMiniGraph = {
    render: renderMiniGraph,
    destroy,
    layerOf,
    LAYER_COLOR,
  };
})(window);
