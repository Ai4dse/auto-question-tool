import React, { useCallback, useEffect, useMemo, useRef } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  Handle,
  Position,
  BaseEdge,
  EdgeLabelRenderer,
  getStraightPath,
  addEdge,
  reconnectEdge,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

/* ---------------- SHARED STYLES ---------------- */

const HANDLE_SIZE = 14;

const relationHandleStyle = {
  width: HANDLE_SIZE,
  height: HANDLE_SIZE,
  borderRadius: "50%",
  background: "#f6a623",
  border: "1px solid #333",
  zIndex: 5,
};

const attributeHandleStyle = {
  width: HANDLE_SIZE,
  height: HANDLE_SIZE,
  borderRadius: "50%",
  background: "#cfe2ff",
  border: "1px solid #333",
  zIndex: 5,
};

const transparentInputStyle = {
  border: "none",
  background: "transparent",
  textAlign: "center",
  outline: "none",
};

const entityBoxStyle = {
  minWidth: 190,
  border: "2px solid #333",
  borderRadius: 6,
  background: "#97c95c",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  position: "relative",
  padding: "20px 12px",
};

const weakEntityBoxStyle = {
  ...entityBoxStyle,
  boxShadow: "inset 0 0 0 4px #97c95c, inset 0 0 0 6px #333",
};


const relationWrapperStyle = {
  width: 140,
  height: 120,
  position: "relative",
};

const relationDiamondStyle = {
  width: 110,
  height: 110,
  margin: "0 auto",
  transform: "rotate(45deg)",
  background: "#f6a623",
  border: "2px solid #333",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const weakRelationDiamondStyle = {
  ...relationDiamondStyle,
  boxShadow: "inset 0 0 0 4px #f6a623, inset 0 0 0 6px #333",
};

const relationInnerStyle = {
  transform: "rotate(-45deg)",
};

const attributeNodeStyle = {
  minWidth: 150,
  minHeight: 70,
  border: "2px solid #333",
  borderRadius: "50%",
  background: "#cfe2ff",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  position: "relative",
  padding: "14px 18px",
  cursor: "default",
  userSelect: "none",
};

/* ---------------- NODE COMPONENTS ---------------- */

function EntityNode({ id, data }) {
  return (
    <div
      onDoubleClick={(e) => {
        e.stopPropagation();
        data.onToggleWeak(id);
      }}
      style={data.isWeak ? weakEntityBoxStyle : entityBoxStyle}
    >
      <Handle
        id="relation-left"
        type="target"
        position={Position.Left}
        isConnectableStart={false}
        isConnectableEnd={true}
        style={{
          ...relationHandleStyle,
          left: -10,
          top: "50%",
          transform: "translateY(-50%)",
        }}
      />

      <Handle
        id="relation-right"
        type="target"
        position={Position.Right}
        isConnectableStart={false}
        isConnectableEnd={true}
        style={{
          ...relationHandleStyle,
          right: -10,
          top: "50%",
          transform: "translateY(-50%)",
        }}
      />

      <Handle
        id="attribute-top"
        type="target"
        position={Position.Top}
        isConnectableStart={false}
        isConnectableEnd={true}
        style={{
          ...attributeHandleStyle,
          top: -10,
          left: "50%",
          transform: "translateX(-50%)",
        }}
      />

      <input
        value={data.label}
        onChange={(e) => data.onLabelChange(id, e.target.value)}
        onKeyDown={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
        style={{
          ...transparentInputStyle,
          fontWeight: "bold",
          width: "100%",
        }}
      />
    </div>
  );
}

function RelationNode({ id, data }) {
  return (
    <div
      onDoubleClick={(e) => {
        e.stopPropagation();
        data.onToggleWeak(id);
      }}
      style={relationWrapperStyle}
    >
      <Handle
        id="left"
        type="source"
        position={Position.Left}
        isConnectableStart={true}
        isConnectableEnd={false}
        style={{
          ...relationHandleStyle,
          left: -10,
          top: 48,
          transform: "none",
        }}
      />

      <Handle
        id="right"
        type="source"
        position={Position.Right}
        isConnectableStart={true}
        isConnectableEnd={false}
        style={{
          ...relationHandleStyle,
          right: -10,
          top: 48,
          transform: "none",
        }}
      />

      <Handle
        id="bottom"
        type="source"
        position={Position.Bottom}
        isConnectableStart={true}
        isConnectableEnd={false}
        style={{
          ...relationHandleStyle,
          bottom: -15,
          left: "50%",
          transform: "translateX(-50%)",
        }}
      />

      <Handle
        id="attribute-top"
        type="target"
        position={Position.Top}
        isConnectableStart={false}
        isConnectableEnd={true}
        style={{
          ...attributeHandleStyle,
          top: -25,
          left: "50%",
          transform: "translateX(-50%)",
        }}
      />

      <div style={data.isWeak ? weakRelationDiamondStyle : relationDiamondStyle}>
        <div style={relationInnerStyle}>
          <input
            value={data.label}
            onChange={(e) => data.onLabelChange(id, e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            onPointerDown={(e) => e.stopPropagation()}
            style={{
              ...transparentInputStyle,
              fontWeight: "bold",
            }}
          />
        </div>
      </div>
    </div>
  );
}

function AttributeNode({ id, data }) {
  return (
    <div
      onDoubleClick={(e) => {
        e.stopPropagation();
        data.onToggleKey(id);
      }}
      style={attributeNodeStyle}
    >
      <Handle
        id="attribute-source"
        type="source"
        position={Position.Bottom}
        isConnectableStart={true}
        isConnectableEnd={false}
        style={{
          ...attributeHandleStyle,
          bottom: -10,
          left: "50%",
          transform: "translateX(-50%)",
        }}
      />

      <input
        value={data.label}
        onChange={(e) => data.onLabelChange(id, e.target.value)}
        onKeyDown={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
        style={{
          ...transparentInputStyle,
          width: "100%",
          fontWeight: data.isKey ? "bold" : "normal",
          textDecoration: data.isKey ? "underline" : "none",
        }}
      />
    </div>
  );
}

/* ---------------- EDGE COMPONENT ---------------- */

function ERValueEdge(props) {
  const { id, sourceX, sourceY, targetX, targetY, data } = props;
  const [path] = getStraightPath({ sourceX, sourceY, targetX, targetY });

  const dx = sourceX - targetX;
  const dy = sourceY - targetY;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const px = -dy / dist;
  const py = dx / dist;

  const ratioFromTarget = 0.55;
  const offset = 12;

  const labelX = targetX + (sourceX - targetX) * ratioFromTarget + px * offset;
  const labelY = targetY + (sourceY - targetY) * ratioFromTarget + py * offset;

  return (
    <>
      <BaseEdge path={path} style={{ stroke: "#555", strokeWidth: 2 }} />

      {data?.showLabel && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: "all",
              zIndex: 1000,
              background: "#fff",
              padding: "2px 4px",
              border: "1px solid #ccc",
              borderRadius: 6,
            }}
          >
            <input
              type="text"
              value={data.value ?? ""}
              placeholder="1..n"
              maxLength={10}
              onChange={(e) => data.onValueChange(id, e.target.value)}
              onKeyDown={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
              style={{
                width: 56,
                minWidth: 56,
                height: 24,
                border: "1px solid #ccc",
                borderRadius: 4,
                fontSize: 12,
                padding: "1px 4px",
                textAlign: "center",
                outline: "none",
              }}
            />
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

/* ---------------- MAIN COMPONENT ---------------- */

export default function ERDiagramBuilder({ el, idx, onChange }) {
  const id = el.id || `er_builder_${idx}`;
  const relationFieldId = `${id}:relations`;
  const diagramStateFieldId = `${id}:diagram_state`;
  const flowHeight = el.height ?? 700;
  const initialDiagram = el.initial_diagram ?? { nodes: [], edges: [] };

  const [nodes, setNodes, onNodesChange] = useNodesState(
    initialDiagram.nodes || []
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    initialDiagram.edges || []
  );

  const lastExport = useRef("");
  const lastDiagramExport = useRef("");

  const getNode = useCallback(
    (nodeId) => nodes.find((n) => n.id === nodeId),
    [nodes]
  );

  const updateNodeLabel = useCallback((nodeId, value) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, label: value } } : n
      )
    );
  }, []);

  const toggleAttributeKey = useCallback((nodeId) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId && n.type === "attribute"
          ? {
              ...n,
              data: {
                ...n.data,
                isKey: !n.data?.isKey,
              },
            }
          : n
      )
    );
  }, []);

  const updateEdgeValue = useCallback((edgeId, value) => {
    setEdges((eds) =>
      eds.map((e) =>
        e.id === edgeId ? { ...e, data: { ...e.data, value } } : e
      )
    );
  }, []);

  const removeSelected = useCallback(() => {
    const selectedNodeIds = new Set(
      nodes.filter((n) => n.selected).map((n) => n.id)
    );
    const selectedEdgeIds = new Set(
      edges.filter((e) => e.selected).map((e) => e.id)
    );

    setEdges((eds) =>
      eds.filter(
        (e) =>
          !selectedEdgeIds.has(e.id) &&
          !selectedNodeIds.has(e.source) &&
          !selectedNodeIds.has(e.target)
      )
    );

    setNodes((nds) => nds.filter((n) => !selectedNodeIds.has(n.id)));
  }, [nodes, edges]);

  useEffect(() => {
    const isTypingElement = (target) => {
      if (!target) return false;
      const tag = target.tagName?.toLowerCase();

      return (
        tag === "input" ||
        tag === "textarea" ||
        tag === "select" ||
        target.isContentEditable
      );
    };

    const handleKeyDown = (e) => {
      if (e.key !== "Backspace" && e.key !== "Delete") return;
      if (isTypingElement(document.activeElement)) return;

      e.preventDefault();
      removeSelected();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [removeSelected]);

  const validateConnection = useCallback(
    (connection, ignoreEdgeId = null) => {
      const { source, target, sourceHandle, targetHandle } = connection;
      const sourceNode = getNode(source);
      const targetNode = getNode(target);

      if (!sourceNode || !targetNode) return false;
      if (sourceNode.id === targetNode.id) return false;

      const relevantEdges = edges.filter((e) => e.id !== ignoreEdgeId);

      if (sourceNode.type === "relation" && targetNode.type === "entity") {
        if (!["left", "right", "bottom"].includes(sourceHandle)) return false;
        if (!["relation-left", "relation-right"].includes(targetHandle)) {
            return false;
        }

        const relationEdges = relevantEdges.filter((e) => e.source === source);

        if (relationEdges.some((e) => e.sourceHandle === sourceHandle)) {
            return false;
        }

        return true;
      }

      if (
        sourceNode.type === "attribute" &&
        (targetNode.type === "entity" || targetNode.type === "relation")
      ) {
        if (sourceHandle !== "attribute-source") return false;
        if (targetHandle !== "attribute-top") return false;

        const attributeEdges = relevantEdges.filter((e) => e.source === source);
        if (attributeEdges.length >= 1) return false;

        return true;
      }

      return false;
    },
    [edges, getNode]
  );

  const onConnect = useCallback(
    (connection) => {
      if (!validateConnection(connection)) return;

      const sourceNode = getNode(connection.source);
      const showLabel = sourceNode?.type === "relation";

      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            type: "erValueEdge",
            data: {
              value: "",
              showLabel,
              onValueChange: updateEdgeValue,
            },
          },
          eds
        )
      );
    },
    [validateConnection, getNode, updateEdgeValue]
  );

  const onReconnect = useCallback(
    (oldEdge, newConnection) => {
      if (!validateConnection(newConnection, oldEdge.id)) return;

      setEdges((eds) =>
        reconnectEdge(
          oldEdge,
          {
            ...newConnection,
            type: oldEdge.type,
            data: oldEdge.data,
          },
          eds
        )
      );
    },
    [validateConnection]
  );

    const toggleWeakNode = useCallback((nodeId) => {
        setNodes((nds) =>
            nds.map((n) =>
            n.id === nodeId && (n.type === "entity" || n.type === "relation")
                ? {
                    ...n,
                    data: {
                    ...n.data,
                    isWeak: !n.data?.isWeak,
                    },
                }
                : n
            )
        );
    }, []);

  const addEntity = useCallback(() => {
    setNodes((nds) => {
        const count = nds.filter((n) => n.type === "entity").length + 1;

        return [
        ...nds,
        {
            id: `entity_${crypto.randomUUID()}`,
            type: "entity",
            position: { x: 100 + count * 40, y: 80 + count * 30 },
            data: {
            label: `ENTITY_${count}`,
            isWeak: false,
            onLabelChange: updateNodeLabel,
            onToggleWeak: toggleWeakNode,
            },
        },
        ];
    });
    }, [updateNodeLabel, toggleWeakNode]);

    const addRelation = useCallback(() => {
    setNodes((nds) => {
        const count = nds.filter((n) => n.type === "relation").length + 1;

        return [
        ...nds,
        {
            id: `relation_${crypto.randomUUID()}`,
            type: "relation",
            position: { x: 350 + count * 40, y: 220 + count * 30 },
            data: {
            label: `relation_${count}`,
            isWeak: false,
            onLabelChange: updateNodeLabel,
            onToggleWeak: toggleWeakNode,
            },
        },
        ];
    });
    }, [updateNodeLabel, toggleWeakNode]);

  const addAttribute = useCallback(() => {
    setNodes((nds) => {
      const count = nds.filter((n) => n.type === "attribute").length + 1;

      return [
        ...nds,
        {
          id: `attribute_${crypto.randomUUID()}`,
          type: "attribute",
          position: { x: 180 + count * 35, y: 420 + count * 25 },
          data: {
            label: `attribute_${count}`,
            isKey: false,
            onLabelChange: updateNodeLabel,
            onToggleKey: toggleAttributeKey,
          },
        },
      ];
    });
  }, [updateNodeLabel, toggleAttributeKey]);

  useEffect(() => {
    setNodes((nds) =>
        nds.map((n) => ({
        ...n,
        data: {
            ...n.data,
            onLabelChange: updateNodeLabel,
            ...(n.type === "attribute" ? { onToggleKey: toggleAttributeKey } : {}),
            ...(
            n.type === "entity" || n.type === "relation"
                ? { onToggleWeak: toggleWeakNode }
                : {}
            ),
        },
        }))
    );

    setEdges((eds) =>
        eds.map((e) => ({
        ...e,
        data: {
            ...e.data,
            onValueChange: updateEdgeValue,
        },
        }))
    );
    }, [updateNodeLabel, toggleAttributeKey, toggleWeakNode, updateEdgeValue]);

  useEffect(() => {
    const serializableNodes = nodes.map((n) => ({
        id: n.id,
        type: n.type,
        position: n.position,
        data:
            n.type === "attribute"
            ? {
                label: n.data?.label ?? "",
                isKey: !!n.data?.isKey,
                }
            : {
                label: n.data?.label ?? "",
                isWeak: !!n.data?.isWeak,
                },
        }));

    const serializableEdges = edges.map((e) => ({
      id: e.id,
      source: e.source,
      sourceHandle: e.sourceHandle,
      target: e.target,
      targetHandle: e.targetHandle,
      type: e.type,
      data: {
        value: e.data?.value ?? "",
        showLabel: !!e.data?.showLabel,
      },
    }));

    const diagramState = {
      nodes: serializableNodes,
      edges: serializableEdges,
    };

    const json = JSON.stringify(diagramState);

    if (json === lastDiagramExport.current) return;
    lastDiagramExport.current = json;

    onChange(diagramStateFieldId, json);
  }, [nodes, edges, onChange, diagramStateFieldId]);

  useEffect(() => {
    const entityNodes = nodes.filter((n) => n.type === "entity");
    const relationNodes = nodes.filter((n) => n.type === "relation");
    const attributeNodes = nodes.filter((n) => n.type === "attribute");

    const entities = entityNodes.map((entity) => ({
        name: entity.data?.label || entity.id,
        is_weak: !!entity.data?.isWeak,
        attributes: [],
    }));

    const relations = relationNodes.map((relation) => {
        const relationEdges = edges.filter((e) => e.source === relation.id);

        return {
            name: relation.data?.label || relation.id,
            is_weak: !!relation.data?.isWeak,
            attributes: [],
            entities: relationEdges.map((e) => {
            const entity = getNode(e.target);
            return {
                name: entity?.data?.label || e.target,
                value: e.data?.value ?? "",
            };
            }),
        };
    });

    const entityMap = Object.fromEntries(
      entityNodes.map((entity, index) => [entity.id, entities[index]])
    );

    const relationMap = Object.fromEntries(
      relationNodes.map((relation, index) => [relation.id, relations[index]])
    );

    attributeNodes.forEach((attr) => {
      const edge = edges.find((e) => e.source === attr.id);
      if (!edge) return;

      const owner = getNode(edge.target);
      if (!owner) return;

      const attrObj = {
        name: attr.data?.label || attr.id,
        is_key: !!attr.data?.isKey,
      };

      if (owner.type === "entity" && entityMap[owner.id]) {
        entityMap[owner.id].attributes.push(attrObj);
      }

      if (owner.type === "relation" && relationMap[owner.id]) {
        relationMap[owner.id].attributes.push(attrObj);
      }
    });

    const output = {
      entities,
      relations,
    };

    const json = JSON.stringify(output);

    if (json === lastExport.current) return;
    lastExport.current = json;

    onChange(relationFieldId, json);
  }, [nodes, edges, getNode, onChange, relationFieldId]);

  const nodeTypes = useMemo(
    () => ({
      entity: EntityNode,
      relation: RelationNode,
      attribute: AttributeNode,
    }),
    []
  );

  const edgeTypes = useMemo(
    () => ({
      erValueEdge: ERValueEdge,
    }),
    []
  );

  return (
    <div className="card mb-4 shadow-sm">
      <div className="card-body">
        <div
          className="border rounded"
          style={{ width: "100%", height: flowHeight, background: "#fafafa" }}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onReconnect={onReconnect}
            fitView
            deleteKeyCode={null}
          >
            <Background />
            <Controls />
            <MiniMap />

            <Panel position="top-left">
              <div className="d-flex flex-column gap-2">
                <button className="btn btn-sm btn-primary" onClick={addEntity}>
                  Add Entity
                </button>

                <button className="btn btn-sm btn-warning" onClick={addRelation}>
                  Add Relation
                </button>

                <button className="btn btn-sm btn-info" onClick={addAttribute}>
                  Add Attribute
                </button>

                <button
                  className="btn btn-sm btn-outline-danger"
                  onClick={removeSelected}
                >
                  Delete Selected
                </button>
              </div>
            </Panel>
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}