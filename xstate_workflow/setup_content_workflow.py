"""
Setup Content Post Workflow

Creates a workflow for automated content generation and publishing:
1. Start - Initial state when content post is created
2. Research Topic - AI researches the topic based on user input
3. Get Trends - AI fetches latest trends related to the topic
4. Generate Content - AI generates platform-specific content
5. Review - Human reviews and approves/rejects content
6. Publish - AI publishes content to selected platforms
7. End - Final published state

Run with: bench --site xs.local execute xstate_workflow.setup_content_workflow.setup
"""

import frappe
import json


def setup():
    """Create the Content Post Workflow"""

    workflow_name = "Content Post Workflow"

    # XState configuration
    xstate_config = {
        "id": workflow_name,
        "version": "1",
        "initial": "start",
        "context": {
            "research_results": None,
            "trends": None,
            "generated_at": None,
            "published_at": None,
        },
        "states": {
            "start": {
                "meta": {
                    "domain_node": {
                        "type": "start",
                        "label": "Start"
                    }
                },
                "on": {
                    "BEGIN_RESEARCH": "research_topic"
                }
            },
            "research_topic": {
                "meta": {
                    "domain_node": {
                        "type": "agentic",
                        "label": "Research Topic",
                        "agent_type": "react",
                        "system_prompt": """You are a research assistant helping to gather information for content creation.

Your task is to research the topic based on the user's prompt and industry focus.

Research the following:
1. Key facts and statistics related to the topic
2. Recent news or developments
3. Expert opinions or quotes
4. Relevant case studies or examples

Store your findings in a structured format that can be used for content generation.

After completing your research, trigger the RESEARCH_COMPLETE event with a summary of your findings.""",
                        "model": "claude-sonnet",
                        "frappe_access": {
                            "read_doc": True,
                            "write_doc": True,
                        },
                        "data_input": {
                            "include_current_doc": True,
                            "fields": ["prompt", "industry_focus", "content_themes", "target_audience"]
                        },
                        "transition_mode": "event",
                        "custom_events": [
                            {"name": "RESEARCH_COMPLETE", "description": "Research is complete, proceed to trends analysis"}
                        ],
                        "max_iterations": 10,
                        "timeout_seconds": 300
                    }
                },
                "on": {
                    "RESEARCH_COMPLETE": "get_trends"
                }
            },
            "get_trends": {
                "meta": {
                    "domain_node": {
                        "type": "agentic",
                        "label": "Get Trends",
                        "agent_type": "react",
                        "system_prompt": """You are a trends analyst specializing in social media and industry trends.

Your task is to identify the latest trends relevant to the content topic.

Analyze:
1. Current trending hashtags related to the industry
2. Popular content formats that are performing well
3. Timing considerations for posting
4. Viral content patterns in this space

Use web search to find the most current trends.

After completing your analysis, trigger the TRENDS_COMPLETE event.""",
                        "model": "claude-sonnet",
                        "enabled_tools": [
                            {"name": "web_search", "enabled": True}
                        ],
                        "frappe_access": {
                            "read_doc": True,
                            "write_doc": True,
                        },
                        "data_input": {
                            "include_current_doc": True,
                            "include_context": True
                        },
                        "transition_mode": "event",
                        "custom_events": [
                            {"name": "TRENDS_COMPLETE", "description": "Trends analysis complete, proceed to content generation"}
                        ],
                        "max_iterations": 8,
                        "timeout_seconds": 180
                    }
                },
                "on": {
                    "TRENDS_COMPLETE": "generate_content"
                }
            },
            "generate_content": {
                "meta": {
                    "domain_node": {
                        "type": "agentic",
                        "label": "Generate Content",
                        "agent_type": "react",
                        "system_prompt": """You are an expert content creator specializing in social media and professional content.

Using the research and trends data from the context, generate engaging content for the target platforms.

Generate the following:
1. **Title**: A compelling title for the content piece
2. **Topic Brief**: A 2-3 sentence summary of the topic
3. **Twitter Version**: Max 280 characters, punchy and engaging with relevant hashtags
4. **LinkedIn Version**: Professional tone, 1-3 paragraphs with a call to action
5. **Newsletter Version**: Longer form, educational, with clear sections
6. **Hashtags**: 5-10 relevant hashtags

Update the document with all generated content using the write_doc tool.

After updating all fields, trigger the CONTENT_GENERATED event.""",
                        "model": "claude-sonnet",
                        "frappe_access": {
                            "read_doc": True,
                            "write_doc": True,
                        },
                        "data_input": {
                            "include_current_doc": True,
                            "include_context": True
                        },
                        "transition_mode": "event",
                        "custom_events": [
                            {"name": "CONTENT_GENERATED", "description": "Content has been generated, proceed to review"}
                        ],
                        "max_iterations": 10,
                        "timeout_seconds": 300
                    }
                },
                "on": {
                    "CONTENT_GENERATED": "review"
                }
            },
            "review": {
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "Review Content",
                        "resolver": {
                            "type": "role",
                            "role": "System Manager"
                        },
                        "available_actions": ["Approve", "Reject", "Request Changes"],
                        "sla_hours": 24,
                        "priority": "Medium"
                    }
                },
                "on": {
                    "Approve": "publish",
                    "Reject": "rejected",
                    "Request Changes": "generate_content"
                }
            },
            "publish": {
                "meta": {
                    "domain_node": {
                        "type": "agentic",
                        "label": "Publish Content",
                        "agent_type": "react",
                        "system_prompt": """You are a publishing assistant responsible for posting content to social media platforms.

Your task is to publish the approved content to the target platforms specified in the document.

For this demo:
1. Log that you would publish to each platform
2. Update the published_urls field with simulated URLs
3. Update the status to indicate successful publishing

After completing publishing, trigger the PUBLISHED event.""",
                        "model": "claude-haiku",
                        "frappe_access": {
                            "read_doc": True,
                            "write_doc": True,
                        },
                        "data_input": {
                            "include_current_doc": True,
                            "fields": ["title", "twitter_version", "linkedin_version", "target_platforms"]
                        },
                        "transition_mode": "event",
                        "custom_events": [
                            {"name": "PUBLISHED", "description": "Content has been published successfully"},
                            {"name": "PUBLISH_FAILED", "description": "Publishing failed, needs retry or manual intervention"}
                        ],
                        "max_iterations": 5,
                        "timeout_seconds": 120
                    }
                },
                "on": {
                    "PUBLISHED": "published",
                    "PUBLISH_FAILED": "publish_failed"
                }
            },
            "published": {
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "label": "Published",
                        "final_status": "Published"
                    }
                },
                "type": "final"
            },
            "rejected": {
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "label": "Rejected",
                        "final_status": "Rejected"
                    }
                },
                "type": "final"
            },
            "publish_failed": {
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "label": "Failed",
                        "final_status": "Failed"
                    }
                },
                "type": "final"
            }
        }
    }

    # Builder config with flow-based positions
    # Positions calculated for left-to-right flow
    builder_config = {
        "id": workflow_name,
        "name": workflow_name,
        "version": 1,
        "nodes": [
            {
                "id": "node_1",
                "type": "start",
                "position": {"x": 100, "y": 200},
                "data": {
                    "label": "Start",
                    "stateName": "start",
                    "xstateType": "atomic",
                    "domainType": "start",
                    "isInitial": True
                }
            },
            {
                "id": "node_2",
                "type": "agentic",
                "position": {"x": 400, "y": 200},
                "data": {
                    "label": "Research Topic",
                    "stateName": "research_topic",
                    "xstateType": "atomic",
                    "domainType": "agentic"
                }
            },
            {
                "id": "node_3",
                "type": "agentic",
                "position": {"x": 700, "y": 200},
                "data": {
                    "label": "Get Trends",
                    "stateName": "get_trends",
                    "xstateType": "atomic",
                    "domainType": "agentic"
                }
            },
            {
                "id": "node_4",
                "type": "agentic",
                "position": {"x": 1000, "y": 200},
                "data": {
                    "label": "Generate Content",
                    "stateName": "generate_content",
                    "xstateType": "atomic",
                    "domainType": "agentic"
                }
            },
            {
                "id": "node_5",
                "type": "approval",
                "position": {"x": 1300, "y": 200},
                "data": {
                    "label": "Review Content",
                    "stateName": "review",
                    "xstateType": "atomic",
                    "domainType": "approval"
                }
            },
            {
                "id": "node_6",
                "type": "agentic",
                "position": {"x": 1600, "y": 200},
                "data": {
                    "label": "Publish Content",
                    "stateName": "publish",
                    "xstateType": "atomic",
                    "domainType": "agentic"
                }
            },
            {
                "id": "node_7",
                "type": "end",
                "position": {"x": 1900, "y": 100},
                "data": {
                    "label": "Published",
                    "stateName": "published",
                    "xstateType": "final",
                    "domainType": "end"
                }
            },
            {
                "id": "node_8",
                "type": "end",
                "position": {"x": 1600, "y": 400},
                "data": {
                    "label": "Rejected",
                    "stateName": "rejected",
                    "xstateType": "final",
                    "domainType": "end"
                }
            },
            {
                "id": "node_9",
                "type": "end",
                "position": {"x": 1900, "y": 300},
                "data": {
                    "label": "Failed",
                    "stateName": "publish_failed",
                    "xstateType": "final",
                    "domainType": "end"
                }
            }
        ],
        "edges": [
            {
                "id": "edge_1",
                "source": "node_1",
                "target": "node_2",
                "type": "transition",
                "data": {"event": "BEGIN_RESEARCH", "transitionType": "event"}
            },
            {
                "id": "edge_2",
                "source": "node_2",
                "target": "node_3",
                "type": "transition",
                "data": {"event": "RESEARCH_COMPLETE", "transitionType": "event"}
            },
            {
                "id": "edge_3",
                "source": "node_3",
                "target": "node_4",
                "type": "transition",
                "data": {"event": "TRENDS_COMPLETE", "transitionType": "event"}
            },
            {
                "id": "edge_4",
                "source": "node_4",
                "target": "node_5",
                "type": "transition",
                "data": {"event": "CONTENT_GENERATED", "transitionType": "event"}
            },
            {
                "id": "edge_5",
                "source": "node_5",
                "target": "node_6",
                "type": "transition",
                "data": {"event": "Approve", "transitionType": "event"}
            },
            {
                "id": "edge_6",
                "source": "node_5",
                "target": "node_8",
                "type": "transition",
                "data": {"event": "Reject", "transitionType": "event"}
            },
            {
                "id": "edge_7",
                "source": "node_5",
                "target": "node_4",
                "type": "transition",
                "data": {"event": "Request Changes", "transitionType": "event"}
            },
            {
                "id": "edge_8",
                "source": "node_6",
                "target": "node_7",
                "type": "transition",
                "data": {"event": "PUBLISHED", "transitionType": "event"}
            },
            {
                "id": "edge_9",
                "source": "node_6",
                "target": "node_9",
                "type": "transition",
                "data": {"event": "PUBLISH_FAILED", "transitionType": "event"}
            }
        ]
    }

    # Create the State Machine document
    machine_id = "content-post-workflow"

    # Delete existing by machine_id if exists
    if frappe.db.exists("State Machine", machine_id):
        frappe.delete_doc("State Machine", machine_id, force=True)
        frappe.db.commit()
        print(f"Deleted existing workflow with ID: {machine_id}")

    doc = frappe.get_doc({
        "doctype": "State Machine",
        "machine_id": machine_id,
        "title": workflow_name,
        "attached_doctype": "Content Post",
        "is_active": 1,
        "json_config": json.dumps(xstate_config, indent=2),
        "workflow_builder_config": json.dumps(builder_config, indent=2)
    })
    doc.insert()
    frappe.db.commit()

    print(f"Created workflow: {workflow_name}")
    print(f"Attached to: Content Post")
    print(f"States: {list(xstate_config['states'].keys())}")
    print("\nWorkflow Flow:")
    print("  Start -> Research Topic -> Get Trends -> Generate Content -> Review")
    print("  Review -> Approve -> Publish -> Published")
    print("  Review -> Reject -> Rejected")
    print("  Review -> Request Changes -> Generate Content (loop)")
    print("  Publish -> Failed (on error)")

    return doc.name


if __name__ == "__main__":
    setup()
