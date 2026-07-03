import React, { useCallback, useEffect, useMemo, useRef } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { v4 as uuidv4 } from "uuid";

const ROOT_ID = "root";
const HORIZONTAL_GAP = 170;
const VERTICAL_GAP = 145;
const EMPTY_NODE_RESULTS = Object.freeze({});

const nodeShellBaseStyle = {
  minWidth: 122,
  border: "2px solid #333",
  borderRadius: 8,
  background: "#fff",
  overflow: "hidden",
  boxShadow: "0 2px 4px rgba(0,0,0,0.08)",
  userSelect: "none",
};

const gridStyle = {
  display: "grid",
  gridTemplateColumns: "1fr 56px",
};

const labelCellBaseStyle = {
  minHeight: 74,
  padding: "8px 8px 6px",
  borderRight: "2px solid #333",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 6,
};

const countCellBaseStyle = {
  minHeight: 74,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  gap: 3,
  padding: "4px 2px",
};

const smallButtonStyle = {
  width: 26,
  height: 22,
  lineHeight: "18px",
  padding: 0,
  border: "1px solid #555",
  borderRadius: 4,
  background: "#f8f9fa",
  fontWeight: "bold",
  cursor: "pointer",
};

const selectStyle = {
  width: "100%",
  minWidth: 74,
  border: "1px solid #aaa",
  borderRadius: 4,
  padding: "2px 4px",
  textAlign: "center",
  fontWeight: "bold",
  background: "#fff",
};

const rootLabelStyle = {
  width: "100%",
  border: "1px solid #aaa",
  borderRadius: 4,
  padding: "3px 4px",
  textAlign: "center",
  fontWeight: "bold",
  background: "#f1f3f5",
};

function resultBackground(result, part = "node") {
  if (!result) return {};

  if (part === "label") {
    if (result.name_correct === true) return { background: "var(--bs-success-bg-subtle)" };
    if (result.name_correct === false) return { background: "var(--bs-danger-bg-subtle)" };
    return {};
  }

  if (part === "count") {
    if (result.count_correct === true) return { background: "var(--bs-success-bg-subtle)" };
    if (result.count_correct === false) return { background: "var(--bs-danger-bg-subtle)" };
    return {};
  }

  if (result.correct === true) return { background: "var(--bs-success-bg-subtle)" };
  if (result.name_correct === true || result.count_correct === true) {
    return { background: "var(--bs-warning-bg-subtle)" };
  }
  return { background: "var(--bs-danger-bg-subtle)" };
}

function resultTitle(result) {
  if (!result) return "";
  const parts = [];
  if (result.expected_path) parts.push(`Expected path: ${result.expected_path}`);
  if (result.expected_name !== undefined) parts.push(`Expected item: ${result.expected_name}`);
  if (result.expected_count !== undefined) parts.push(`Expected count: ${result.expected_count}`);
  if (result.message) parts.push(result.message);
  return parts.join("\n");
}

function FPTreeNode({ id, data }) {
  const isRoot = !!data.isRoot;
  const count = Number.isFinite(Number(data.count)) ? Number(data.count) : isRoot ? 0 : 1;
  const evalResult = data.evalResult;
  const canAddChild = data.canAddChild !== false;

  const itemOptions = Array.from(
    new Set([
      ...(data.availableItems || []),
      ...(!isRoot && data.label ? [String(data.label)] : []),
    ])
  );

  return (
    <div
      style={{ ...nodeShellBaseStyle, ...resultBackground(evalResult) }}
      title={resultTitle(evalResult)}
    >
      <Handle
        id="top"
        type="target"
        position={Position.Top}
        isConnectable={false}
        style={{ opacity: 0 }}
      />
      <Handle
        id="bottom"
        type="source"
        position={Position.Bottom}
        isConnectable={false}
        style={{ opacity: 0 }}
      />

      <div style={gridStyle}>
        <div style={{ ...labelCellBaseStyle, ...resultBackground(evalResult, "label") }}>
          {isRoot ? (
            <div style={rootLabelStyle}>root</div>
          ) : (
            <select
              className="nodrag nopan"
              value={data.label || ""}
              onChange={(e) => data.onLabelChange(id, e.target.value)}
              onKeyDown={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
              style={selectStyle}
            >
              {itemOptions.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          )}

          <button
            type="button"
            className="nodrag nopan"
            title={canAddChild ? "Add child node" : "All available items are already used as children"}
            disabled={!canAddChild}
            onClick={(e) => {
              e.stopPropagation();
              if (!canAddChild) return;
              data.onAddChild(id);
            }}
            onPointerDown={(e) => e.stopPropagation()}
            style={{
              ...smallButtonStyle,
              opacity: canAddChild ? 1 : 0.45,
              cursor: canAddChild ? "pointer" : "not-allowed",
            }}
          >
            +
          </button>
        </div>

        <div style={{ ...countCellBaseStyle, ...resultBackground(evalResult, "count") }}>
          <button
            type="button"
            className="nodrag nopan"
            title="Increase count"
            onClick={(e) => {
              e.stopPropagation();
              data.onCountChange(id, 1);
            }}
            onPointerDown={(e) => e.stopPropagation()}
            style={smallButtonStyle}
          >
            +
          </button>

          <div style={{ fontWeight: "bold", minWidth: 24, textAlign: "center" }}>
            {count}
          </div>

          <button
            type="button"
            className="nodrag nopan"
            title="Decrease count"
            onClick={(e) => {
              e.stopPropagation();
              data.onCountChange(id, -1);
            }}
            onPointerDown={(e) => e.stopPropagation()}
            style={smallButtonStyle}
          >
            -
          </button>
        </div>
      </div>
    </div>
  );
}

function makeRootNode(callbacks, availableItems, evalResult) {
  return {
    id: ROOT_ID,
    type: "fpTreeNode",
    position: { x: 0, y: 0 },
    data: {
      label: "root",
      count: 0,
      isRoot: true,
      availableItems,
      evalResult,
      ...callbacks,
    },
  };
}

function stripRuntimeNodeData(node) {
  return {
    id: node.id,
    type: node.type || "fpTreeNode",
    position: node.position || { x: 0, y: 0 },
    data: {
      label: node.id === ROOT_ID ? "root" : node.data?.label ?? "",
      count: Number.isFinite(Number(node.data?.count)) ? Number(node.data.count) : node.id === ROOT_ID ? 0 : 1,
      isRoot: node.id === ROOT_ID || !!node.data?.isRoot,
    },
  };
}

function stripRuntimeEdgeData(edge) {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle || "bottom",
    targetHandle: edge.targetHandle || "top",
    type: edge.type || "smoothstep",
  };
}

function treeToInitialFlow(tree, availableItems) {
  if (!tree || typeof tree !== "object") return { nodes: [], edges: [] };

  const nodes = [];
  const edges = [];

  const walk = (treeNode, parentId, depth, index, siblingCount) => {
    const isRoot = !parentId;
    const nodeId = isRoot ? ROOT_ID : treeNode.id || `fp_node_${uuidv4()}`;
    const offset = index - (siblingCount - 1) / 2;

    nodes.push({
      id: nodeId,
      type: "fpTreeNode",
      position: {
        x: isRoot ? 0 : offset * HORIZONTAL_GAP + depth * 20,
        y: depth * VERTICAL_GAP,
      },
      data: {
        label: isRoot ? "root" : String(treeNode.name ?? treeNode.label ?? availableItems[0] ?? "A"),
        count: Number(treeNode.count ?? treeNode.value ?? (isRoot ? 0 : 1)),
        isRoot,
      },
    });

    if (parentId) {
      edges.push({
        id: `fp_edge_${uuidv4()}`,
        source: parentId,
        sourceHandle: "bottom",
        target: nodeId,
        targetHandle: "top",
        type: "smoothstep",
      });
    }

    const children = Array.isArray(treeNode.children)
      ? treeNode.children
      : Array.isArray(treeNode.childreen)
      ? treeNode.childreen
      : [];

    children.forEach((child, childIndex) => {
      walk(child, nodeId, depth + 1, childIndex, children.length);
    });
  };

  walk(tree, null, 0, 0, 1);
  return { nodes, edges };
}

export default function FPTreeBuilder({
  el,
  idx,
  onChange,
  evaluationResults,
  showExpected = false,
  registerFieldId,
}) {
  const id = el.id || `fp_tree_builder_${idx}`;
  const rowsFieldId = `${id}:rows`;
  const treeStateFieldId = `${id}:tree_state`;
  const flowHeight = el.height ?? 620;

  const availableItemsRaw = el.available_items || el.availableItems || [];
  const availableItemsKey = Array.isArray(availableItemsRaw)
    ? availableItemsRaw.map(String).join("\u001f")
    : "";

  const availableItems = useMemo(
    () => (Array.isArray(availableItemsRaw) ? availableItemsRaw : []).map(String),
    [availableItemsKey]
  );

  const fallbackItem = availableItems[0] || "A";
  const evalForField = evaluationResults?.[id];
  const nodeResultsRaw = evalForField?.node_results || EMPTY_NODE_RESULTS;
  const nodeResultsKey = JSON.stringify(nodeResultsRaw);
  const nodeResults = useMemo(() => nodeResultsRaw, [nodeResultsKey]);

  const lastTreeExport = useRef("");
  const lastRowsExport = useRef("");
  const lastVisualExport = useRef("");

  useEffect(() => {
    if (typeof registerFieldId === "function") registerFieldId(String(id));
  }, [registerFieldId, id]);

  const initialFlow = useMemo(() => {
    const initialState = el.initial_tree_state || el.initialTreeState || null;
    if (initialState?.nodes?.length) {
      return {
        nodes: initialState.nodes.map(stripRuntimeNodeData),
        edges: (initialState.edges || []).map(stripRuntimeEdgeData),
      };
    }

    const initialTree = el.initial_tree || el.initialTree || null;
    const fromTree = treeToInitialFlow(initialTree, availableItems);
    if (fromTree.nodes.length) return fromTree;

    return { nodes: [makeRootNode({}, availableItems, undefined)], edges: [] };
  }, [el.initial_tree_state, el.initialTreeState, el.initial_tree, el.initialTree, availableItems]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialFlow.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialFlow.edges);

  const updateNodeLabel = useCallback(
    (nodeId, value) => {
      const nextValue = String(value || "");

      setNodes((currentNodes) => {
        const parentId = edges.find((edge) => edge.target === nodeId)?.source;

        if (parentId) {
          const duplicateSibling = edges.some((edge) => {
            if (edge.source !== parentId || edge.target === nodeId) return false;
            const sibling = currentNodes.find((node) => node.id === edge.target);
            return String(sibling?.data?.label || "") === nextValue;
          });

          if (duplicateSibling) return currentNodes;
        }

        return currentNodes.map((node) =>
          node.id === nodeId && node.id !== ROOT_ID
            ? { ...node, data: { ...node.data, label: nextValue } }
            : node
        );
      });
    },
    [edges]
  );

  const updateNodeCount = useCallback((nodeId, delta) => {
    setNodes((currentNodes) =>
      currentNodes.map((node) => {
        if (node.id !== nodeId) return node;
        const current = Number.isFinite(Number(node.data?.count))
          ? Number(node.data.count)
          : node.id === ROOT_ID
          ? 0
          : 1;
        const minValue = node.id === ROOT_ID ? 0 : 1;
        return {
          ...node,
          data: {
            ...node.data,
            count: Math.max(minValue, current + delta),
          },
        };
      })
    );
  }, []);

  const addChildNode = useCallback(
    (parentId) => {
      setNodes((currentNodes) => {
        const parent = currentNodes.find((node) => node.id === parentId);
        if (!parent) return currentNodes;

        const candidateItems = availableItems.length ? availableItems : [fallbackItem];
        const childEdges = edges.filter((edge) => edge.source === parentId);
        const usedChildLabels = new Set(
          childEdges
            .map((edge) => currentNodes.find((node) => node.id === edge.target)?.data?.label)
            .filter((label) => label !== undefined && label !== null && String(label).trim() !== "")
            .map(String)
        );

        const nextLabel = candidateItems.find((item) => !usedChildLabels.has(String(item)));
        if (!nextLabel) return currentNodes;

        const childCount = childEdges.length;
        const newNodeId = `fp_node_${uuidv4()}`;
        const childX = parent.position.x + (childCount - 0.5) * HORIZONTAL_GAP;
        const childY = parent.position.y + VERTICAL_GAP;

        setEdges((currentEdges) => [
          ...currentEdges,
          {
            id: `fp_edge_${uuidv4()}`,
            source: parentId,
            sourceHandle: "bottom",
            target: newNodeId,
            targetHandle: "top",
            type: "smoothstep",
          },
        ]);

        return [
          ...currentNodes,
          {
            id: newNodeId,
            type: "fpTreeNode",
            position: { x: childX, y: childY },
            data: {
              label: String(nextLabel),
              count: 1,
              isRoot: false,
              availableItems,
              onAddChild: addChildNode,
              onLabelChange: updateNodeLabel,
              onCountChange: updateNodeCount,
            },
          },
        ];
      });
    },
    [edges, fallbackItem, availableItems, updateNodeLabel, updateNodeCount]
  );

  const removeSelected = useCallback(() => {
    const selectedNodeIds = new Set(
      nodes.filter((node) => node.selected && node.id !== ROOT_ID).map((node) => node.id)
    );
    const selectedEdgeIds = new Set(edges.filter((edge) => edge.selected).map((edge) => edge.id));
    if (!selectedNodeIds.size && !selectedEdgeIds.size) return;

    const childMap = new Map();
    edges.forEach((edge) => {
      if (!childMap.has(edge.source)) childMap.set(edge.source, []);
      childMap.get(edge.source).push(edge.target);
    });

    const subtreeIds = new Set(selectedNodeIds);
    const collectChildren = (nodeId) => {
      (childMap.get(nodeId) || []).forEach((childId) => {
        if (childId === ROOT_ID || subtreeIds.has(childId)) return;
        subtreeIds.add(childId);
        collectChildren(childId);
      });
    };
    selectedNodeIds.forEach(collectChildren);

    setEdges((currentEdges) =>
      currentEdges.filter(
        (edge) =>
          !selectedEdgeIds.has(edge.id) &&
          !subtreeIds.has(edge.source) &&
          !subtreeIds.has(edge.target)
      )
    );
    setNodes((currentNodes) => currentNodes.filter((node) => !subtreeIds.has(node.id)));
  }, [nodes, edges]);

  const resetTree = useCallback(() => {
    setNodes([makeRootNode({}, availableItems, undefined)]);
    setEdges([]);
  }, [availableItems]);

  useEffect(() => {
    setNodes((currentNodes) => {
      let changed = false;

      const parentByChild = new Map();
      const childrenByParent = new Map();

      edges.forEach((edge) => {
        parentByChild.set(edge.target, edge.source);
        if (!childrenByParent.has(edge.source)) childrenByParent.set(edge.source, []);
        childrenByParent.get(edge.source).push(edge.target);
      });

      const labelByNodeId = new Map(
        currentNodes.map((node) => [
          node.id,
          node.id === ROOT_ID ? "root" : String(node.data?.label || fallbackItem),
        ])
      );

      const nextNodes = currentNodes.map((node) => {
        const currentData = node.data || {};
        const nextLabel = node.id === ROOT_ID ? "root" : String(currentData.label || fallbackItem);
        const nextCount = Number.isFinite(Number(currentData.count))
          ? Number(currentData.count)
          : node.id === ROOT_ID
          ? 0
          : 1;
        const nextIsRoot = node.id === ROOT_ID || !!currentData.isRoot;
        const nextEvalResult = nodeResults[node.id];

        const parentId = parentByChild.get(node.id);
        const siblingLabels = new Set(
          (childrenByParent.get(parentId) || [])
            .filter((childId) => childId !== node.id)
            .map((childId) => labelByNodeId.get(childId))
            .filter(Boolean)
        );

        const nextAvailableItems = nextIsRoot
          ? availableItems
          : Array.from(
              new Set([
                ...availableItems.filter(
                  (item) => String(item) === nextLabel || !siblingLabels.has(String(item))
                ),
                nextLabel,
              ])
            );

        const candidateChildItems = availableItems.length ? availableItems : [fallbackItem];
        const usedChildLabels = new Set(
          (childrenByParent.get(node.id) || [])
            .map((childId) => labelByNodeId.get(childId))
            .filter(Boolean)
        );
        const nextCanAddChild = candidateChildItems.some((item) => !usedChildLabels.has(String(item)));

        const currentItemsKey = Array.isArray(currentData.availableItems)
          ? currentData.availableItems.map(String).join("\u001f")
          : "";
        const nextItemsKey = nextAvailableItems.map(String).join("\u001f");

        const needsUpdate =
          node.type !== "fpTreeNode" ||
          currentData.label !== nextLabel ||
          Number(currentData.count) !== nextCount ||
          !!currentData.isRoot !== nextIsRoot ||
          currentItemsKey !== nextItemsKey ||
          currentData.canAddChild !== nextCanAddChild ||
          currentData.evalResult !== nextEvalResult ||
          currentData.onAddChild !== addChildNode ||
          currentData.onLabelChange !== updateNodeLabel ||
          currentData.onCountChange !== updateNodeCount;

        if (!needsUpdate) return node;
        changed = true;

        return {
          ...node,
          type: "fpTreeNode",
          data: {
            ...currentData,
            label: nextLabel,
            count: nextCount,
            isRoot: nextIsRoot,
            availableItems: nextAvailableItems,
            canAddChild: nextCanAddChild,
            evalResult: nextEvalResult,
            onAddChild: addChildNode,
            onLabelChange: updateNodeLabel,
            onCountChange: updateNodeCount,
          },
        };
      });

      return changed ? nextNodes : currentNodes;
    });
  }, [
    addChildNode,
    updateNodeLabel,
    updateNodeCount,
    fallbackItem,
    availableItems,
    availableItemsKey,
    nodeResults,
    edges,
  ]);

  useEffect(() => {
    const isTypingElement = (target) => {
      if (!target) return false;
      const tag = target.tagName?.toLowerCase();
      return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable;
    };

    const handleKeyDown = (event) => {
      if (event.key !== "Backspace" && event.key !== "Delete") return;
      if (isTypingElement(document.activeElement)) return;
      event.preventDefault();
      removeSelected();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [removeSelected]);

  const treeAndRows = useMemo(() => {
    const nodeMap = new Map(nodes.map((node) => [node.id, node]));
    const childrenByParent = new Map();

    edges.forEach((edge) => {
      if (!nodeMap.has(edge.source) || !nodeMap.has(edge.target)) return;
      if (!childrenByParent.has(edge.source)) childrenByParent.set(edge.source, []);
      childrenByParent.get(edge.source).push(edge.target);
    });

    const rows = [];
    const visited = new Set();

    const build = (nodeId, prefix) => {
      if (visited.has(nodeId)) return null;
      visited.add(nodeId);

      const node = nodeMap.get(nodeId);
      if (!node) return null;

      const isRoot = nodeId === ROOT_ID;
      const name = isRoot ? "root" : String(node.data?.label || fallbackItem);
      const count = Number.isFinite(Number(node.data?.count))
        ? Number(node.data.count)
        : isRoot
        ? 0
        : 1;

      const childIds = (childrenByParent.get(nodeId) || [])
        .map((childId) => nodeMap.get(childId))
        .filter(Boolean)
        .sort((a, b) =>
          a.position.y - b.position.y || a.position.x - b.position.x || a.id.localeCompare(b.id)
        )
        .map((child) => child.id);

      const children = [];
      childIds.forEach((childId) => {
        const childTree = build(childId, isRoot ? [] : [...prefix, name]);
        if (!childTree) return;
        children.push(childTree);

        const childPath = isRoot
          ? [childTree.name]
          : [...prefix, name, childTree.name];
        rows.push({ path: childPath.join(", "), count: String(childTree.count) });
      });

      return { id: nodeId, name, count, children };
    };

    const tree = build(ROOT_ID, []) || { id: ROOT_ID, name: "root", count: 0, children: [] };
    return { tree, rows };
  }, [nodes, edges, fallbackItem]);

  useEffect(() => {
    const json = JSON.stringify(treeAndRows.tree);
    if (json === lastTreeExport.current) return;
    lastTreeExport.current = json;
    onChange(id, json);
  }, [treeAndRows.tree, id, onChange]);

  useEffect(() => {
    const json = JSON.stringify({ rows: treeAndRows.rows });
    if (json === lastRowsExport.current) return;
    lastRowsExport.current = json;
    onChange(rowsFieldId, json);
  }, [treeAndRows.rows, rowsFieldId, onChange]);

  useEffect(() => {
    const visualState = {
      nodes: nodes.map(stripRuntimeNodeData),
      edges: edges.map(stripRuntimeEdgeData),
    };
    const json = JSON.stringify(visualState);
    if (json === lastVisualExport.current) return;
    lastVisualExport.current = json;
    onChange(treeStateFieldId, json);
  }, [nodes, edges, onChange, treeStateFieldId]);

  const nodeTypes = useMemo(() => ({ fpTreeNode: FPTreeNode }), []);
  const fieldEvalClass =
    evalForField === undefined ? "" : evalForField.correct ? "border-success" : "border-danger";

  return (
    <div className={`card mb-4 shadow-sm ${fieldEvalClass}`}>
      <div className="card-body">
        {el.label && <h6 className="mb-2">{el.label}</h6>}

        {showExpected && evalForField && !evalForField.correct && Array.isArray(evalForField.missing) && evalForField.missing.length > 0 && (
          <div className="alert alert-warning py-2 small">
            Missing nodes: {evalForField.missing.map((m) => `${m.path} (${m.count})`).join(", ")}
          </div>
        )}

        <div
          className="border rounded"
          style={{ width: "100%", height: flowHeight, background: "#fafafa" }}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            deleteKeyCode={null}
            nodesDraggable
            nodesConnectable={false}
            elementsSelectable
          >
            <Background />
            <Controls />
            <MiniMap />

            <Panel position="top-left">
              <div className="d-flex flex-column gap-2">
                <button className="btn btn-sm btn-outline-danger" type="button" onClick={removeSelected}>
                  Delete selected
                </button>
                <button className="btn btn-sm btn-outline-secondary" type="button" onClick={resetTree}>
                  Reset tree
                </button>
              </div>
            </Panel>
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}
