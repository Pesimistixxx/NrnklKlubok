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
  const resizeObservers = new WeakMap();
  const resizeTimers = new WeakMap();
  const RESIZE_DEBOUNCE_MS = 150;

  function bindCameraStable(network, inst) {
    if (inst._cameraBound || !network) return;
    inst._cameraBound = true;
    inst.userMovedCamera = !!inst.userMovedCamera;
    network.on("dragStart", () => { inst.userMovedCamera = true; });
    network.on("zoom", () => { inst.userMovedCamera = true; });
  }

  function debouncedViewportRefresh(container, inst, { fit = false } = {}) {
    const prev = resizeTimers.get(container);
    if (prev) clearTimeout(prev);
    resizeTimers.set(container, setTimeout(() => {
      resizeTimers.delete(container);
      if (!inst?.network) return;
      inst.network.redraw();
      if (fit && !inst.userMovedCamera) {
        inst.network.fit({ animation: { duration: 180, easingFunction: "easeInOutQuad" } });
      }
    }, RESIZE_DEBOUNCE_MS));
  }

  function attachResizeObserver(container, inst) {
    if (resizeObservers.has(container) || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => debouncedViewportRefresh(container, inst, { fit: false }));
    ro.observe(container);
    resizeObservers.set(container, ro);
  }

  function detachGraphObservers(container) {
    const ro = resizeObservers.get(container);
    if (ro) {
      ro.disconnect();
      resizeObservers.delete(container);
    }
    const t = resizeTimers.get(container);
    if (t) {
      clearTimeout(t);
      resizeTimers.delete(container);
    }
  }

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
    detachGraphObservers(container);
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

    const inst = { network, dataSets, edgeSeq: visEdges.length, userMovedCamera: false, hasInitialFit: false };
    bindCameraStable(network, inst);
    attachResizeObserver(container, inst);
    instances.set(container, inst);
    return network;
  }

  function mergeGraphs(a, b) {
    return normalizeGraph({
      ...(a || {}),
      nodes: [...(a?.nodes || []), ...(b?.nodes || [])],
      relationships: [...(a?.relationships || []), ...(b?.relationships || [])],
      document_ids: [...new Set([...(a?.document_ids || []), ...(b?.document_ids || [])])],
    });
  }

  /** Incrementally add nodes/edges to an existing mini-graph (live orchestrator updates). */
  function mergeInto(container, graph, opts = {}) {
    if (!container) return null;
    const normalized = normalizeGraph(graph || {});
    const nodes = normalized.nodes || [];
    const rels = normalized.relationships || [];
    if (!nodes.length && !rels.length) return null;

    let inst = instances.get(container);
    if (!inst?.network || typeof vis === "undefined") {
      return renderMiniGraph(container, normalized, opts);
    }

    const { dataSets, network } = inst;
    bindCameraStable(network, inst);
    attachResizeObserver(container, inst);
    const existingIds = new Set(dataSets.nodes.get().map((n) => n.id));
    const animate = opts.animate !== false;
    const newVisNodes = [];
    for (const n of nodes) {
      if (existingIds.has(n.id)) continue;
      existingIds.add(n.id);
      const built = buildVisItems([n], [], { animate: false }).visNodes[0];
      if (built) {
        if (animate) {
          built.hidden = true;
          built.opacity = 0;
        }
        newVisNodes.push(built);
      }
    }
    if (newVisNodes.length) {
      dataSets.nodes.add(newVisNodes);
      if (animate) {
        newVisNodes.forEach((u, idx) => {
          setTimeout(() => dataSets.nodes.update({ id: u.id, hidden: false, opacity: 1 }), idx * 40);
        });
      }
    }

    let edgeSeq = inst.edgeSeq ?? dataSets.edges.length;
    const existingEdgeKeys = new Set(
      dataSets.edges.get().map((e) => `${e.from}|${e.to}`)
    );
    const nodeIds = new Set(dataSets.nodes.get().map((n) => n.id));
    for (const r of rels) {
      const { from, to } = relEndpoints(r);
      if (!from || !to || !nodeIds.has(from) || !nodeIds.has(to)) continue;
      const key = `${from}|${to}`;
      if (existingEdgeKeys.has(key)) continue;
      existingEdgeKeys.add(key);
      const traversed = !!(r.props && r.props._traversed);
      const edge = {
        id: `e${edgeSeq}`,
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
      dataSets.edges.add(edge);
      if (animate) {
        setTimeout(() => dataSets.edges.update({ id: edge.id, hidden: false }), 80);
      }
      edgeSeq += 1;
    }
    inst.edgeSeq = edgeSeq;

    if (newVisNodes.length) {
      if (!inst.userMovedCamera) {
        network.setOptions({ physics: { enabled: true } });
        let fitted = false;
        network.once("stabilizationIterationsDone", () => {
          if (fitted || inst.userMovedCamera) {
            network.setOptions({ physics: { enabled: false } });
            return;
          }
          fitted = true;
          if (!inst.hasInitialFit) {
            network.fit({ animation: { duration: 220, easingFunction: "easeInOutQuad" } });
            inst.hasInitialFit = true;
          }
          setTimeout(() => network.setOptions({ physics: { enabled: false } }), 260);
        });
      } else {
        network.redraw();
      }
    }
    return network;
  }

  const GRAPH_WALK_UI_STEP_MS = 1300;
  const WALK_NODE_FADE_MS = 350;
  const WALK_EDGE_FADE_MS = 350;
  const WALK_STEP_OVERLAP_MS = 220;
  const WALK_FOCUS_SCALE = 1.015;
  const WALK_FOCUS_EASING = "easeInOutQuart";
  const WALK_HIGHLIGHT_BORDER = "#ffb74d";
  const WALK_HIGHLIGHT_EDGE = "rgba(255, 183, 77, 0.92)";

  function parseColor(input) {
    if (!input) return { r: 176, g: 190, b: 197, a: 1 };
    const s = String(input).trim();
    const rgba = s.match(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)/i);
    if (rgba) {
      return { r: +rgba[1], g: +rgba[2], b: +rgba[3], a: rgba[4] != null ? +rgba[4] : 1 };
    }
    const hex = s.replace("#", "");
    if (hex.length >= 6) {
      return {
        r: parseInt(hex.slice(0, 2), 16),
        g: parseInt(hex.slice(2, 4), 16),
        b: parseInt(hex.slice(4, 6), 16),
        a: 1,
      };
    }
    return { r: 176, g: 190, b: 197, a: 1 };
  }

  function rgbaStr(c) {
    const a = Math.max(0, Math.min(1, c.a));
    return `rgba(${Math.round(c.r)}, ${Math.round(c.g)}, ${Math.round(c.b)}, ${a.toFixed(3)})`;
  }

  function lerpColor(a, b, t) {
    return {
      r: a.r + (b.r - a.r) * t,
      g: a.g + (b.g - a.g) * t,
      b: a.b + (b.b - a.b) * t,
      a: a.a + (b.a - a.a) * t,
    };
  }

  function easeInOutQuad(t) {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  }

  function runTween({ duration, onUpdate, onDone, isCancelled }) {
    const start = performance.now();
    let rafId = null;
    const tick = (now) => {
      if (isCancelled?.()) return;
      const raw = Math.min(1, (now - start) / duration);
      const eased = easeInOutQuad(raw);
      onUpdate(eased, raw);
      if (raw < 1) {
        rafId = requestAnimationFrame(tick);
      } else if (onDone) {
        onDone();
      }
    };
    rafId = requestAnimationFrame(tick);
    return () => {
      if (rafId) cancelAnimationFrame(rafId);
    };
  }

  function nodeStyleSnapshot(origNodes, nodeId) {
    const orig = origNodes.get(nodeId);
    if (!orig) return null;
    return {
      borderWidth: orig.borderWidth ?? 1.5,
      color: orig.color ? JSON.parse(JSON.stringify(orig.color)) : {},
    };
  }

  function edgeStyleSnapshot(origEdges, edgeId) {
    const orig = origEdges.get(edgeId);
    if (!orig) return null;
    return {
      width: orig.width ?? 1,
      color: orig.color ? JSON.parse(JSON.stringify(orig.color)) : {},
    };
  }

  function tweenNodeStyle(dataSets, nodeId, fromStyle, toStyle, duration, isCancelled) {
    if (!nodeId || !fromStyle || !toStyle) return () => {};
    const fromBorder = parseColor(fromStyle.color?.border);
    const toBorder = parseColor(toStyle.color?.border);
    const fromBg = parseColor(fromStyle.color?.background);
    const toBg = parseColor(toStyle.color?.background);
    const fromBw = fromStyle.borderWidth ?? 1.5;
    const toBw = toStyle.borderWidth ?? 2.5;
    return runTween({
      duration,
      isCancelled,
      onUpdate: (eased) => {
        dataSets.nodes.update({
          id: nodeId,
          borderWidth: fromBw + (toBw - fromBw) * eased,
          color: {
            ...(toStyle.color || {}),
            border: rgbaStr(lerpColor(fromBorder, toBorder, eased)),
            background: rgbaStr(lerpColor(fromBg, toBg, eased)),
            highlight: toStyle.color?.highlight || { background: "#01579b", border: "#fff" },
          },
        });
      },
      onDone: () => {
        dataSets.nodes.update({ id: nodeId, borderWidth: toStyle.borderWidth, color: toStyle.color });
      },
    });
  }

  function tweenEdgeStyle(dataSets, edgeId, fromStyle, toStyle, duration, isCancelled) {
    if (!edgeId || !fromStyle || !toStyle) return () => {};
    const fromColor = parseColor(fromStyle.color?.color || fromStyle.color);
    const toColor = parseColor(toStyle.color?.color || toStyle.color);
    const fromWidth = fromStyle.width ?? 1;
    const toWidth = toStyle.width ?? 2.1;
    return runTween({
      duration,
      isCancelled,
      onUpdate: (eased) => {
        dataSets.edges.update({
          id: edgeId,
          width: fromWidth + (toWidth - fromWidth) * eased,
          color: { color: rgbaStr(lerpColor(fromColor, toColor, eased)) },
        });
      },
      onDone: () => {
        dataSets.edges.update({ id: edgeId, color: toStyle.color, width: toStyle.width });
      },
    });
  }

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

  function highlightWalkPath(containerOrNetwork, walkPath, { intervalMs = GRAPH_WALK_UI_STEP_MS, onStep = null, initialDelayMs = 320 } = {}) {
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
    let prevNodeStyle = null;
    let prevEdgeIds = [];
    let cancelled = false;
    let timerId = null;
    const activeTweens = [];
    const isCancelled = () => cancelled;
    const stopTweens = () => {
      while (activeTweens.length) {
        const stop = activeTweens.pop();
        try { stop(); } catch { /* ignore */ }
      }
    };
    const pushTween = (stop) => {
      if (typeof stop === "function") activeTweens.push(stop);
    };

    const focusDuration = Math.min(intervalMs * 0.72, 920);
    const stepGapMs = Math.max(480, intervalMs - WALK_STEP_OVERLAP_MS);

    const highlightStep = (step) => {
      const nid = step.node_id;
      if (prevNodeId && prevNodeId !== nid) {
        const orig = nodeStyleSnapshot(origNodes, prevNodeId);
        if (orig && prevNodeStyle) {
          pushTween(tweenNodeStyle(dataSets, prevNodeId, prevNodeStyle, orig, WALK_NODE_FADE_MS, isCancelled));
        }
      }
      prevEdgeIds.forEach((eid) => {
        const orig = edgeStyleSnapshot(origEdges, eid);
        if (!orig) return;
        const current = dataSets.edges.get(eid);
        const fromStyle = edgeStyleSnapshot(
          new Map([[eid, { width: current?.width, color: current?.color }]]),
          eid,
        );
        if (fromStyle) {
          pushTween(tweenEdgeStyle(dataSets, eid, fromStyle, orig, WALK_EDGE_FADE_MS, isCancelled));
        }
      });
      prevEdgeIds = [];

      if (nid) {
        const orig = nodeStyleSnapshot(origNodes, nid);
        const highlightStyle = {
          borderWidth: 2.5,
          color: {
            ...(orig?.color || {}),
            border: WALK_HIGHLIGHT_BORDER,
            background: orig?.color?.background || "#0071e3",
            highlight: { background: "#01579b", border: "#fff" },
          },
        };
        const currentNode = dataSets.nodes.get(nid);
        const fromStyle = nodeStyleSnapshot(
          new Map([[nid, { borderWidth: currentNode?.borderWidth, color: currentNode?.color }]]),
          nid,
        ) || orig;
        if (fromStyle) {
          pushTween(tweenNodeStyle(dataSets, nid, fromStyle, highlightStyle, WALK_NODE_FADE_MS, isCancelled));
          prevNodeStyle = highlightStyle;
        }
        try {
          network.selectNodes([nid]);
          network.focus(nid, {
            scale: WALK_FOCUS_SCALE,
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
          const orig = edgeStyleSnapshot(origEdges, e.id);
          const current = dataSets.edges.get(e.id);
          const fromStyle = edgeStyleSnapshot(
            new Map([[e.id, { width: current?.width, color: current?.color }]]),
            e.id,
          ) || orig;
          const highlightStyle = {
            width: 2.1,
            color: { color: WALK_HIGHLIGHT_EDGE },
          };
          if (fromStyle && orig) {
            pushTween(tweenEdgeStyle(dataSets, e.id, fromStyle, highlightStyle, WALK_EDGE_FADE_MS, isCancelled));
          }
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
        timerId = setTimeout(tick, stepGapMs);
      };
      timerId = setTimeout(tick, initialDelayMs);
    });

    const cancel = () => {
      cancelled = true;
      if (timerId) clearTimeout(timerId);
      stopTweens();
    };

    promise.cancel = cancel;
    return promise;
  }

  global.MKGMiniGraph = {
    render: renderMiniGraph,
    destroy,
    normalizeGraph,
    mergeGraphs,
    mergeInto,
    dedupeGraphNodes,
    highlightWalkPath,
    GRAPH_WALK_UI_STEP_MS,
    WALK_NODE_FADE_MS,
    WALK_EDGE_FADE_MS,
    WALK_STEP_OVERLAP_MS,
    refreshViewport(container, { fit = false } = {}) {
      const inst = instances.get(container);
      if (!inst?.network) return;
      debouncedViewportRefresh(container, inst, { fit: fit && !inst.userMovedCamera });
    },
    layerOf,
    LAYER_COLOR,
  };
})(window);
