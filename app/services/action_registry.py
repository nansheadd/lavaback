"""
Action Registry - Defines all available actions that can be used in workflows.

Each action has:
- id: Unique identifier (e.g., "email.send")
- name: Human-readable name
- category: Group (data, communication, logic, external, utility)
- description: What the action does
- inputs: Expected input parameters
- outputs: What the action returns
- handler: Function to execute the action
"""

from typing import Any, Dict, List, Callable
from dataclasses import dataclass, field
import json


@dataclass
class ActionInput:
    name: str
    type: str  # string, number, boolean, object, array
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass
class ActionDefinition:
    id: str
    name: str
    category: str
    description: str
    inputs: List[ActionInput] = field(default_factory=list)
    outputs: Dict[str, str] = field(default_factory=dict)
    handler: Callable = None


class ActionRegistry:
    """
    Central registry for all workflow actions.
    """
    
    def __init__(self):
        self._actions: Dict[str, ActionDefinition] = {}
        self._register_builtin_actions()
    
    def register(self, action: ActionDefinition):
        """Register a new action."""
        self._actions[action.id] = action
    
    def get(self, action_id: str) -> ActionDefinition:
        """Get an action by ID."""
        return self._actions.get(action_id)
    
    def list_all(self) -> List[Dict]:
        """List all registered actions (for API)."""
        return [
            {
                "id": a.id,
                "name": a.name,
                "category": a.category,
                "description": a.description,
                "inputs": [
                    {"name": i.name, "type": i.type, "required": i.required, "default": i.default}
                    for i in a.inputs
                ],
                "outputs": a.outputs
            }
            for a in self._actions.values()
        ]
    
    def list_by_category(self) -> Dict[str, List[Dict]]:
        """List actions grouped by category."""
        result = {}
        for action in self._actions.values():
            if action.category not in result:
                result[action.category] = []
            result[action.category].append({
                "id": action.id,
                "name": action.name,
                "description": action.description
            })
        return result
    
    def _register_builtin_actions(self):
        """Register all built-in actions."""
        
        # === DATA ACTIONS ===
        self.register(ActionDefinition(
            id="data.log",
            name="Log Message",
            category="utility",
            description="Log a message to the execution log",
            inputs=[
                ActionInput("message", "string", True, description="Message to log")
            ],
            outputs={"logged": "boolean"},
            handler=self._action_log
        ))
        
        self.register(ActionDefinition(
            id="data.set_variable",
            name="Set Variable",
            category="utility",
            description="Set a variable in the workflow context",
            inputs=[
                ActionInput("name", "string", True, description="Variable name"),
                ActionInput("value", "any", True, description="Variable value")
            ],
            outputs={"success": "boolean"},
            handler=self._action_set_variable
        ))
        
        self.register(ActionDefinition(
            id="data.transform",
            name="Transform Data",
            category="data",
            description="Transform input data using a template",
            inputs=[
                ActionInput("template", "object", True, description="Output template with {{variable}} placeholders")
            ],
            outputs={"result": "object"},
            handler=self._action_transform
        ))
        
        # === COMMUNICATION ACTIONS ===
        self.register(ActionDefinition(
            id="email.send",
            name="Send Email",
            category="communication",
            description="Send an email (simulated)",
            inputs=[
                ActionInput("to", "string", True, description="Recipient email"),
                ActionInput("subject", "string", True, description="Email subject"),
                ActionInput("body", "string", True, description="Email body (HTML allowed)")
            ],
            outputs={"sent": "boolean", "message_id": "string"},
            handler=self._action_send_email
        ))
        
        self.register(ActionDefinition(
            id="notification.push",
            name="Push Notification",
            category="communication",
            description="Send a push notification (simulated)",
            inputs=[
                ActionInput("title", "string", True),
                ActionInput("message", "string", True),
                ActionInput("user_id", "number", False)
            ],
            outputs={"sent": "boolean"},
            handler=self._action_push_notification
        ))
        
        # === LOGIC ACTIONS ===
        self.register(ActionDefinition(
            id="logic.condition",
            name="Condition (If/Else)",
            category="logic",
            description="Evaluate a condition and branch execution",
            inputs=[
                ActionInput("left", "any", True, description="Left operand"),
                ActionInput("operator", "string", True, description="Operator: ==, !=, >, <, >=, <=, contains"),
                ActionInput("right", "any", True, description="Right operand")
            ],
            outputs={"result": "boolean"},
            handler=self._action_condition
        ))
        
        self.register(ActionDefinition(
            id="logic.delay",
            name="Delay",
            category="utility",
            description="Wait for a specified duration",
            inputs=[
                ActionInput("seconds", "number", True, default=1, description="Seconds to wait")
            ],
            outputs={"waited": "boolean"},
            handler=self._action_delay
        ))
        
        # === EXTERNAL ACTIONS ===
        self.register(ActionDefinition(
            id="http.request",
            name="HTTP Request",
            category="external",
            description="Make an HTTP request to an external API",
            inputs=[
                ActionInput("url", "string", True),
                ActionInput("method", "string", False, default="GET"),
                ActionInput("headers", "object", False, default={}),
                ActionInput("body", "object", False)
            ],
            outputs={"status": "number", "data": "object"},
            handler=self._action_http_request
        ))
    
    # === ACTION HANDLERS ===
    
    async def _action_log(self, context: Dict, config: Dict) -> Dict:
        message = config.get("message", "")
        # Replace variables in message
        for key, value in context.get("variables", {}).items():
            message = message.replace(f"{{{{{key}}}}}", str(value))
        print(f"[WORKFLOW LOG] {message}")
        return {"logged": True, "_log": message}
    
    async def _action_set_variable(self, context: Dict, config: Dict) -> Dict:
        name = config.get("name")
        value = config.get("value")
        if "variables" not in context:
            context["variables"] = {}
        context["variables"][name] = value
        return {"success": True}
    
    async def _action_transform(self, context: Dict, config: Dict) -> Dict:
        template = config.get("template", {})
        result = json.loads(json.dumps(template))  # Deep copy
        # Simple variable replacement
        def replace_vars(obj):
            if isinstance(obj, str):
                for key, value in context.get("variables", {}).items():
                    obj = obj.replace(f"{{{{{key}}}}}", str(value))
                return obj
            elif isinstance(obj, dict):
                return {k: replace_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_vars(i) for i in obj]
            return obj
        return {"result": replace_vars(result)}
    
    async def _action_send_email(self, context: Dict, config: Dict) -> Dict:
        # Simulated email sending - in production, integrate with email service
        to = config.get("to")
        subject = config.get("subject")
        body = config.get("body")
        print(f"[EMAIL] To: {to}, Subject: {subject}")
        return {"sent": True, "message_id": f"msg_{id(config)}"}
    
    async def _action_push_notification(self, context: Dict, config: Dict) -> Dict:
        title = config.get("title")
        message = config.get("message")
        print(f"[NOTIFICATION] {title}: {message}")
        return {"sent": True}
    
    async def _action_condition(self, context: Dict, config: Dict) -> Dict:
        left = config.get("left")
        operator = config.get("operator", "==")
        right = config.get("right")
        
        # Resolve variables
        if isinstance(left, str) and left.startswith("{{") and left.endswith("}}"):
            var_name = left[2:-2]
            left = context.get("variables", {}).get(var_name, left)
        if isinstance(right, str) and right.startswith("{{") and right.endswith("}}"):
            var_name = right[2:-2]
            right = context.get("variables", {}).get(var_name, right)
        
        result = False
        if operator == "==":
            result = left == right
        elif operator == "!=":
            result = left != right
        elif operator == ">":
            result = float(left) > float(right)
        elif operator == "<":
            result = float(left) < float(right)
        elif operator == ">=":
            result = float(left) >= float(right)
        elif operator == "<=":
            result = float(left) <= float(right)
        elif operator == "contains":
            result = str(right) in str(left)
        
        return {"result": result}
    
    async def _action_delay(self, context: Dict, config: Dict) -> Dict:
        import asyncio
        seconds = config.get("seconds", 1)
        await asyncio.sleep(seconds)
        return {"waited": True}
    
    async def _action_http_request(self, context: Dict, config: Dict) -> Dict:
        import aiohttp
        url = config.get("url")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        body = config.get("body")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, json=body) as response:
                    data = await response.json()
                    return {"status": response.status, "data": data}
        except Exception as e:
            return {"status": 0, "data": None, "error": str(e)}


# Global instance
action_registry = ActionRegistry()
