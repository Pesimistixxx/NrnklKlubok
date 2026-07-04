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

  /** Убирает дубликаты узлов по id (vis-network падает на повторах). */
  function dedupeGraphNodes(nodes) {
    const byId = new Map();
    for (const n of nodes || []) {
      const id = String(n.id || "").trim();
      if (!id) continue;
      const prev = byId.get(id);
      if (!prev) {
        byId.set(id, { ...n, props: { ...(n.props || {}) } });
        continue;
      }
      prev.props = { ...(prev.props || {}), ...(n.props || {}) };
      if (!prev.label && n.label) prev.label = n.label;
    }
    return [...byId.values()];
  }

  function dedupeGraphRels(rels, nodeIds) {
    const seen = new Set();
    const out = [];
    for (const r of rels || []) {
      const { from, to } = relEndpoints(r);
      const type = String(r.type || "");
      if (!from || !to || !nodeIds.has(from) || !nodeIds.has(to)) continue;
      const key = `${from}|${type}|${to}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(r);
    }
    return out;
  }

  function normalizeGraph(graph) {
    const nodes = dedupeGraphNodes(graph?.nodes || []);
    const nodeIds = new Set(nodes.map((n) => n.id));
    const relationships = dedupeGraphRels(graph?.relationships || [], nodeIds);
    return { ...graph, nodes, relationships };
  }

  function buildVisItems(nodes, rels, { animate = false } = {}) {
    const visNodes = nodes.map((n) => {
      const props = n.props || {};
      const isSeed = !!props._seed;
      const isVisited = props._visited !== false;
      const walkOrder = props._walk_order;
      const layer = layerOf(n.label);
      const bg = isSeed ? "#0071e3" : (LAYER_COLOR[layer] || LAYER_COLOR["L?"]);
      return {
        id: n.id,
        label: shortLabel(n),
        title: `${n.label}: ${n.id}`,
        color: {
          background: isVisited ? bg : "#b0bec5",
          border: isSeed ? "#004999" : (isVisited ? "#fff" : "#cfd8dc"),
          highlight: { background: "#01579b", border: "#fff" },
        },
        borderWidth: isSeed ? 2.5 : (isVisited ? 1.5 : 1),
        font: { color: "#fff", size: 9, face: "Inter, sans-serif" },
        shape: "box",
        margin: 4,
        widthConstraint: { maximum: 88 },
        level: walkOrder != null ? walkOrder : (isSeed ? 0 : 1),
        hidden: animate,
        opacity: animate ? 0 : 1,
      };
    });
    const visEdges = rels.slice(0, 120).map((r, i) => {
      const { from, to } = relEndpoints(r);
      const traversed = !!(r.props && r.props._traversed);
      return {
        id: `e${i}`,
        from,
        to,
        title: r.type,
        arrows: { to: { enabled: true, scaleFactor: 0.4 } },
        color: {
          color: traversed ? "rgba(2,136,209,0.95)" : "rgba(144,202,249,0.75)",
          highlight: "#0288d1",
        },
        width: traversed ? 2.4 : 0.8,
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
    const normalized = normalizeGraph(graph || {});
    const nodes = normalized.nodes || [];
    const rels = normalized.relationships || [];
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
        delay: idx * 40,
      }));
      nodeUpdates.forEach((u, idx) => {
        setTimeout(() => dataSets.nodes.update({ id: u.id, hidden: false, opacity: 1 }), idx * 45);
      });
      rels.slice(0, 120).forEach((_, idx) => {
        setTimeout(() => {
          const eid = `e${idx}`;
          if (dataSets.edges.get(eid)) dataSets.edges.update({ id: eid, hidden: false });
        }, nodes.length * 45 + idx * 30);
      });
    };

    network.once("stabilizationIterationsDone", () => {
      network.fit({ animation: { duration: 350, easingFunction: "easeInOutQuad" } });
      setTimeout(() => network.setOptions({ physics: { enabled: false } }), 400);
    });

    if (animate) {
      setTimeout(reveal, 60);
    } else {
      dataSets.nodes.update(visNodes.map((n) => ({ id: n.id, hidden: false, opacity: 1 })));
      dataSets.edges.update(visEdges.map((e) => ({ id: e.id, hidden: false })));
    }

    instances.set(container, { network, dataSets });
    return network;
  }

  const GRAPH_WALK_UI_STEP_MS = 900;
  const WALK_FOCUS_EASING = "easeInOutCubic";
  const WALK_HIGHLIGHT_BORDER = "#ffb74d";
  const WALK_HIGHLIGHT_EDGE = "rgba(255, 183, 77, 0.92)";

  function snapshotGraphStyles(dataSets) {
    const nodes = new Map();
    const edges = new Map();
    dataSets.nodes.get().forEach((n) => {
      nodes.set(n.id, {
        borderWidth: n.borderWidth,
        color: n.color ? JSON.parse(JSON.stringify(n.color)) : undefined,
      });
    });
    dataSets.edges.get().forEach((e) => {
      edges.set(e.id, {
        color: e.color ? JSON.parse(JSON.stringify(e.color)) : undefined,
        width: e.width,
      });
    });
    return { nodes, edges };
  }

  function restoreNodeStyle(dataSets, origNodes, nodeId) {
    const orig = origNodes.get(nodeId);
    if (!orig || !nodeId) return;
    dataSets.nodes.update({ id: nodeId, borderWidth: orig.borderWidth, color: orig.color });
  }

  function fadeEdgeStyle(dataSets, origEdges, edgeId, stepMs = 55) {
    const orig = origEdges.get(edgeId);
    if (!orig) return;
    dataSets.edges.update({
      id: edgeId,
      color: { color: "rgba(255, 183, 77, 0.45)" },
      width: Math.max(1, (orig.width || 1) * 1.15),
    });
    setTimeout(() => {
      dataSets.edges.update({ id: edgeId, color: orig.color, width: orig.width });
    }, stepMs * 2);
  }

  function highlightWalkPath(containerOrNetwork, walkPath, { intervalMs = GRAPH_WALK_UI_STEP_MS, onStep = null, initialDelayMs = 280 } = {}) {
    if (!walkPath?.length) return Promise.resolve();
    let inst = instances.get(containerOrNetwork);
    if (!inst) {
      inst = [...instances.values()].find((i) => i.network === containerOrNetwork);
    }
    const dataSets = inst?.dataSets;
    const network = inst?.network;
    if (!dataSets || !network) return Promise.resolve();

    const { nodes: origNodes, edges: origEdges } = snapshotGraphStyles(dataSets);
    let prevNodeId = null;
    let prevEdgeIds = [];
    let cancelled = false;
    let timerId = null;

    const focusDuration = Math.min(intervalMs * 0.58, 520);

    const highlightStep = (step) => {
      const nid = step.node_id;
      if (prevNodeId && prevNodeId !== nid) {
        restoreNodeStyle(dataSets, origNodes, prevNodeId);
      }
      prevEdgeIds.forEach((eid) => fadeEdgeStyle(dataSets, origEdges, eid));
      prevEdgeIds = [];

      if (nid) {
        const orig = origNodes.get(nid);
        dataSets.nodes.update({
          id: nid,
          borderWidth: 2.5,
          color: {
            ...(orig?.color || {}),
            border: WALK_HIGHLIGHT_BORDER,
            background: orig?.color?.background || "#0071e3",
            highlight: { background: "#01579b", border: "#fff" },
          },
        });
        try {
          network.selectNodes([nid]);
          network.focus(nid, {
            scale: 1.03,
            animation: { duration: focusDuration, easingFunction: WALK_FOCUS_EASING },
          });
        } catch { /* ignore */ }
        prevNodeId = nid;
      }
      if (step.from_id && step.rel_type && nid) {
        const edges = dataSets.edges.get({
          filter: (e) => e.from === step.from_id && e.to === nid,
        });
        edges.forEach((e) => {
          dataSets.edges.update({ id: e.id, color: { color: WALK_HIGHLIGHT_EDGE }, width: 2.1 });
          prevEdgeIds.push(e.id);
        });
      }
    };

    const promise = new Promise((resolve) => {
      let idx = 0;
      const tick = () => {
        if (cancelled) {
          resolve();
          return;
        }
        if (idx >= walkPath.length) {
          resolve();
          return;
        }
        const step = walkPath[idx];
        highlightStep(step);
        if (typeof onStep === "function") {
          try { onStep(step, idx, walkPath); } catch { /* ignore */ }
        }
        idx += 1;
        timerId = setTimeout(tick, intervalMs);
      };
      timerId = setTimeout(tick, initialDelayMs);
    });

    const cancel = () => {
      cancelled = true;
      if (timerId) clearTimeout(timerId);
    };

    promise.cancel = cancel;
    return promise;
  }

  global.MKGMiniGraph = {
    render: renderMiniGraph,
    destroy,
    normalizeGraph,
    dedupeGraphNodes,
    highlightWalkPath,
    GRAPH_WALK_UI_STEP_MS,
    refreshViewport(container) {
      const inst = instances.get(container);
      if (!inst?.network) return;
      inst.network.redraw();
      inst.network.fit({ animation: { duration: 200, easingFunction: "easeInOutQuad" } });
    },
    layerOf,
    LAYER_COLOR,
  };
})(window);
