"""
Travel Agent System with Concurrent Execution and Session Management
Non-streaming implementation - returns final response only
"""

import os
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from google.genai import types
from google.generativeai.types import GenerateContentResponse
import copy
import hashlib
from google import genai
# Import from existing structure
from src.chat_history import SQLCache, SessionMessages
from schema.api_structure import UNIFIED_TRAVEL_API
from promptStore.agent_prompt import TravelAgentPrompts
from schema.travel_classes import Task, TaskIteration

# LLM configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
THINKING_BUDGET = int(os.getenv("THINKING_BUDGET", "8000"))
current_date = datetime.now().strftime("%Y-%m-%d")

class TravelAgent:
    """Main travel agent orchestrator with session management"""
    
    def __init__(self, session_id: str, user_query: str, cache: SQLCache = None):
        self.session_id = session_id
        self.user_query = user_query
        
        # Chat history management
        if cache:
            self.cache = cache
        else:
            self.cache = SQLCache(
                session_id=session_id,
                context="travel_agent"
            )
        
        self.session_messages = self.cache.get_session_messages(session_id)
        
        # Core components
        self.api_structure = UNIFIED_TRAVEL_API
        self.prompts = TravelAgentPrompts()
        
        # State management
        self.iterations: List[TaskIteration] = []
        self.current_iteration = 0
        self.max_iterations = 3
        self.extracted_info: Dict[str, Any] = {}
        
        # Execution tracking
        self.task_cache = {}  # Cache for repeated API calls
        
        # Progress tracking (internal)
        self.progress_log = []
        
        # LLM client
        self.client = self._configure_llm()
    
    def _configure_llm(self):
        """Configure LLM client"""
        print(f"Configuring API and Model for Model {GEMINI_MODEL} and API Key")
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            return client
        except Exception as e:
            print(f"❌ LLM configuration failed: {e}")
            return None
    
    def _log_progress(self, message: str):
        """Internal progress logging"""
        timestamp = datetime.now().isoformat()
        self.progress_log.append({
            "timestamp": timestamp,
            "message": message
        })
        print(f"[{timestamp}] {message}")
    
    def generate(self) -> str:
        """Main orchestration function - returns final response text"""
        print(f"\n{'='*60}")
        print(f"🚀 Starting Travel Planning")
        print(f"Session: {self.session_id}")
        print(f"Query: {self.user_query}")
        print(f"{'='*60}\n")
        
        try:
            # Step 1: Root Agent - Clarification
            self._log_progress("🤔 Analyzing your request...")
            
            clarification_result = self._root_agent(THINKING_BUDGET)
            
            if not clarification_result.get('has_sufficient_info'):
                self._log_progress("📝 Formulating clarifying questions...")
                import json
                analysis_json = json.dumps(clarification_result, indent=2)

                chat_context = ""
                try:
                    if self.session_messages:
                        chat_history = self.session_messages.get_message_dicts()
                        chat_context = "\n\nPrevious Conversation:\n"
                        for msg in chat_history[-5:]:
                            role = "User" if msg.get("type") == "human" else "Assistant"
                            chat_context += f"{role}: {msg.get('content', '')}\n"
                except Exception as e:
                    print(f"❌ Error getting chat history: {e}")
                    chat_context = ""

                prompt = f"""
                User's Original Request:
                {self.user_query}

                Recent Conversation History:
                {chat_context}

                My Internal Analysis Report:
                (This report details what I understood and what I'm missing.)
                {analysis_json}
                """

                instructions = """
                You are a friendly and helpful travel planning assistant.
                Your task is to write a single, polite, and conversational response to the user to get the missing information needed to plan their trip.
                You have been given the user's request, the chat history, and an "Internal Analysis Report" (in JSON format).
                Add emojis to the response to make it more friendly and engaging.

                Here's your plan:
                1.  **Acknowledge the Request:** Start with a brief, friendly acknowledgment (e.g., "I can certainly help with that!", "Sounds like a great trip!").
                2.  **Confirm Understood Info (If Any):** Look at the `extracted_info` in the report. If you understood something key (like origin, destination, or dates), briefly mention it.
                3.  **Ask for Missing Info:** Look at the `clarifying_questions` in the report. Weave these into a natural, conversational message. Do not just list them.
                4.  **Tone:** Be helpful and clear, not robotic.
                5.  **Format:** Respond with ONLY the plain text for the user. Do not use Markdown, JSON, or any preamble.
                """

                response_text = self._call_llm(prompt, instructions, True)

                self.session_messages.add_user_message(self.user_query)
                self.session_messages.add_ai_message(response_text)

                return response_text
            hj
            self.extracted_info = clarification_result.get('extracted_info', {})
            self._log_progress(f"✅ Extracted Info: {json.dumps(self.extracted_info, indent=2)}")
            
            # Step 2: Travel Planner - Create task structure
            self._log_progress("📋 Creating travel plan...")
            
            task_structure = self._travel_planner()
            total_tasks = sum(len(tasks) for tasks in task_structure.values())
            self._log_progress(f"✅ Created {total_tasks} tasks across {len(task_structure)} categories")
            
            # Step 3: Execute tasks iteratively
            iteration_count = 0
            while iteration_count < self.max_iterations:
                print(f"\n{'─'*60}")
                print(f"🔄 Iteration {iteration_count + 1}/{self.max_iterations}")
                print(f"{'─'*60}")
                
                self._log_progress(f"⚙️ Processing tasks (Iteration {iteration_count + 1})...")
                
                # Execute current tasks
                execution_results = self._execute_tasks_concurrent(task_structure)
                
                # Store iteration
                current_iteration = TaskIteration(
                    iteration_number=iteration_count + 1,
                    timestamp=datetime.now().isoformat(),
                    tasks=copy.deepcopy(task_structure),
                    execution_summary=execution_results
                )
                self.iterations.append(current_iteration)
                
                self._log_progress(
                    f"Iteration {iteration_count + 1}: "
                    f"{execution_results['completed_count']}/{execution_results['total_count']} tasks completed "
                    f"({execution_results['total_execution_time']:.2f}s)"
                )
                
                # Check if we need more tasks
                if execution_results['completed_count'] == 0:
                    self._log_progress("⚠️ No tasks completed, stopping iterations")
                    break
                
                next_steps = self._determine_next_steps(task_structure)
                
                if not next_steps.get('needs_additional_tasks'):
                    self._log_progress("✅ All necessary tasks completed!")
                    break
                
                # Merge new tasks
                task_structure = self._merge_tasks(task_structure, next_steps.get('new_tasks', {}))
                iteration_count += 1
                
                # Check if we have new tasks to execute
                new_pending = sum(
                    1 for tasks in task_structure.values() 
                    for t in tasks if t.status == "pending"
                )
                if new_pending == 0:
                    self._log_progress("✅ No more pending tasks")
                    break
            
            # Step 4: Generate final summary
            self._log_progress("✨ Preparing your travel plan...")
            
            final_summary = self._generate_final_summary()
            
            # Save to chat history
            self._save_to_history(final_summary)
            
            # Save metadata for debugging/logging
            self._save_execution_metadata()
            
            print(f"\n{'='*60}")
            print(f"✅ Travel Planning Completed Successfully!")
            print(f"{'='*60}\n")
            
            # Return the final text summary
            return final_summary
            
        except Exception as e:
            error_message = f"I apologize, but I encountered an error while planning your trip: {str(e)}\n\nPlease try again or rephrase your request."
            
            print(f"❌ Error in travel planning: {e}")
            import traceback
            traceback.print_exc()
            
            # Save error to history
            try:
                self.session_messages.add_user_message(self.user_query)
                self.session_messages.add_ai_message(error_message)
            except:
                pass
            
            return error_message
    
    def _root_agent(self, thinking_budget) -> Dict[str, Any]:
        """Root agent for clarification"""
        # Get chat history
        chat_history = self.session_messages.get_message_dicts()
        
        prompt, instructions = self.prompts.get_root_agent_prompt(
            self.user_query, 
            chat_history
        )
        
        response = self._call_llm(prompt, instructions, True, thinking_budget)
        result = self._parse_json_response(response)
        
        # Store agent decision
        self.cache.set(
            f"root_agent_decision_{datetime.now().timestamp()}",
            result,
            self.session_id
        )
        
        return result
    
    def _travel_planner(self) -> Dict[str, List[Task]]:
        """Travel planner creates task structure"""
        prompt, instructions = self.prompts.get_travel_planner_prompt(
            self.user_query,
            self.extracted_info
        )
        
        response = self._call_llm(prompt, instructions, False, 0)
        task_json = self._parse_json_response(response)
        
        # Convert JSON to Task objects
        task_structure = {}
        categories = ['flights', 'hotels', 'trains', 'maps']
        
        for category in categories:
            task_list = task_json.get(category, [])
            task_structure[category] = []
            
            for task_data in task_list:
                try:
                    task = Task(
                        task_name=task_data.get('task_name', ''),
                        function=task_data.get('function', ''),
                        request=task_data.get('request', {}),
                        agent_call_required=task_data.get('agent_call_required', False),
                        priority=task_data.get('priority', 0)
                    )
                    task_structure[category].append(task)
                except Exception as e:
                    print(f"⚠️ Failed to create task: {e}")
                    continue
        
        # Store task plan
        self.cache.set(
            f"task_plan_{datetime.now().timestamp()}",
            {cat: [t.to_dict() for t in tasks] for cat, tasks in task_structure.items()},
            self.session_id
        )
        
        return task_structure
    
    def _execute_tasks_concurrent(self, task_structure: Dict[str, List[Task]]) -> Dict[str, Any]:
        """Execute all pending tasks concurrently"""
        import time
        
        # Import tool execution function
        from src.tools_resgistry import execute_tool_by_name
        
        # Collect pending tasks
        pending_tasks = []
        for category, task_list in task_structure.items():
            for task in task_list:
                if task.status == "pending":
                    pending_tasks.append((category, task))
        
        if not pending_tasks:
            return {
                'total_count': 0,
                'completed_count': 0,
                'failed_count': 0,
                'total_execution_time': 0
            }
        
        # Sort by priority (higher first)
        pending_tasks.sort(key=lambda x: x[1].priority, reverse=True)
        
        completed_count = 0
        failed_count = 0
        total_time = 0
        
        # Execute in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_task = {}
            
            for category, task in pending_tasks:
                future = executor.submit(self._execute_single_task, task, execute_tool_by_name)
                future_to_task[future] = (category, task)
            
            for future in as_completed(future_to_task):
                category, task = future_to_task[future]
                try:
                    execution_time = future.result()
                    
                    if task.status == "completed":
                        completed_count += 1
                        status_icon = "✅"
                    elif task.status == "failed":
                        failed_count += 1
                        status_icon = "❌"
                    else:
                        status_icon = "⚠️"
                    
                    total_time += execution_time
                    
                    print(f"{status_icon} [{category}] {task.function} - {execution_time:.2f}s")
                    
                    if task.cached:
                        print(f"   💾 (from cache)")
                    
                    if task.error:
                        print(f"   ⚠️ Error: {task.error[:100]}")
                    
                except Exception as e:
                    task.status = "failed"
                    task.error = str(e)
                    failed_count += 1
                    print(f"❌ [{category}] {task.function} - Exception: {e}")
        
        print(f"\n📊 Execution Summary:")
        print(f"   Total: {len(pending_tasks)} | Completed: {completed_count} | Failed: {failed_count}")
        print(f"   Time: {total_time:.2f}s")
        
        return {
            'total_count': len(pending_tasks),
            'completed_count': completed_count,
            'failed_count': failed_count,
            'total_execution_time': total_time
        }
    
    def _execute_single_task(self, task: Task, execute_func) -> float:
        """Execute a single task with caching and retry logic"""
        import time
        
        start_time = time.time()
        task.status = "in_progress"
        
        # Check cache first
        cache_key = f"task_{task.task_id}"
        cached_response = self.task_cache.get(cache_key)
        
        if cached_response is not None:
            task.response = cached_response
            task.status = "completed"
            task.cached = True
            task.execution_time = time.time() - start_time
            return task.execution_time
        
        # Execute with retry logic
        while task.retry_count < task.max_retries:
            try:
                # Log task execution details
                print(f"\n🚀 [TASK EXEC] Task: {task.task_name}")
                print(f"   🔧 Function: {task.function}")
                print(f"   📋 Request keys: {list(task.request.keys()) if task.request else 'Empty'}")
                print(f"   📋 Request content: {task.request}")
                print(f"   🔄 Retry count: {task.retry_count}/{task.max_retries}")
                
                # Execute the tool
                result = execute_func(task.function, task.request)
                
                # Check for errors
                if isinstance(result, dict) and "error" in result:
                    task.error = result["error"]
                    task.status = "failed"
                else:
                    task.response = result
                    task.status = "completed"
                    
                    # Cache successful response
                    self.task_cache[cache_key] = result
                
                break  # Success or permanent failure
                
            except Exception as e:
                task.retry_count += 1
                task.error = str(e)
                
                if task.retry_count >= task.max_retries:
                    task.status = "failed"
                    print(f"⚠️ Max retries reached for {task.function}")
                else:
                    print(f"🔄 Retry {task.retry_count}/{task.max_retries} for {task.function}")
                    time.sleep(0.5)  # Brief delay before retry
        
        task.execution_time = time.time() - start_time
        return task.execution_time
    
    def _determine_next_steps(self, completed_tasks: Dict[str, List[Task]]) -> Dict[str, Any]:
        """Determine if additional tasks are needed"""
        # Filter tasks that require agent callback
        callback_required = {}
        for category, task_list in completed_tasks.items():
            callback_tasks = [
                t for t in task_list 
                if t.agent_call_required and t.status == "completed"
            ]
            if callback_tasks:
                callback_required[category] = callback_tasks
        
        if not callback_required:
            return {
                'needs_additional_tasks': False,
                'reasoning': 'No tasks require agent callback',
                'ready_for_user': True
            }
        
        prompt, instructions = self.prompts.get_next_steps_prompt(
            callback_required,
            self.user_query
        )
        
        response = self._call_llm(prompt, instructions)
        next_steps = self._parse_json_response(response)
        
        # Convert new tasks to Task objects
        if next_steps.get('new_tasks'):
            for category in ['flights', 'hotels', 'trains', 'maps']:
                task_list = next_steps['new_tasks'].get(category, [])
                next_steps['new_tasks'][category] = []
                
                for task_data in task_list:
                    try:
                        task = Task(
                            task_name=task_data.get('task_name', ''),
                            function=task_data.get('function', ''),
                            request=task_data.get('request', {}),
                            agent_call_required=task_data.get('agent_call_required', False),
                            priority=task_data.get('priority', 0)
                        )
                        next_steps['new_tasks'][category].append(task)
                    except Exception as e:
                        print(f"⚠️ Failed to create subtask: {e}")
                        continue
        
        # Store next steps decision
        if self.iterations:
            self.iterations[-1].agent_decisions.append({
                'timestamp': datetime.now().isoformat(),
                'decision': next_steps
            })
        
        return next_steps
    
    def _generate_final_summary(self) -> str:
        """Generate final user-friendly summary"""
        prompt, instructions = self.prompts.get_final_summary_prompt(
            self.iterations,
            self.user_query
        )
        
        response = self._call_llm(prompt, instructions, True)
        
        # Clean up markdown if needed
        summary = response.strip()
        
        return summary
    
    def _merge_tasks(self, existing: Dict[str, List[Task]], 
                     new: Dict[str, List[Task]]) -> Dict[str, List[Task]]:
        """Merge new tasks into existing structure"""
        merged = copy.deepcopy(existing)
        
        for category in ['flights', 'hotels', 'trains', 'maps']:
            if category in new and new[category]:
                for new_task in new[category]:
                    # Try to find parent task
                    parent_found = False
                    
                    for existing_task in merged[category]:
                        if (existing_task.agent_call_required and 
                            existing_task.status == "completed" and
                            new_task.function.startswith(existing_task.function.split('_')[0])):
                            # Add as subtask
                            new_task.parent_task_id = existing_task.task_id
                            existing_task.subtasks.append(new_task)
                            parent_found = True
                            break
                    
                    # If no parent, add as new top-level task
                    if not parent_found:
                        merged[category].append(new_task)
        
        return merged
    
    def _call_llm(self, prompt: str, instructions: str, toolsNeeded = False ,thinking_budget = 0) -> str:
        """Call LLM with prompt and instructions"""
        if not self.client:
            raise Exception("LLM client not configured")
        
        tools = self._get_tools(toolsNeeded)
        content = self.get_content("user", prompt)
        config = self._get_generate_config(tools, instructions, thinking_budget)
        
        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=content,
                config=config
            )
            return response.text
        except Exception as e:
            print(f"❌ LLM call failed: {e}")
            # Return empty JSON on failure
            return "{}"
    
    def get_content(self, type, prompt):
        role = "system" if type == "system" else "user"
        contents = [
            types.Content(
                role=role,
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
        return contents
    
    def _get_tools(self, tools: bool = False):
        if tools:
            tools = [types.Tool(googleSearch=types.GoogleSearch())]
        else:
            tools = []

        return tools
    
    def _get_generate_config(self, tools, instruction, thinking_budget = 0, res_type = "text/plain"):
        if thinking_budget == 0 and GEMINI_MODEL == "gemini-2.5-pro":
            thinking_budget = -1

        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=thinking_budget,
            ),
            tools=tools,
            system_instruction=[
                instruction
            ],
            response_mime_type= res_type
        )
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM"""
        try:
            # Remove markdown code blocks
            cleaned = re.sub(r"```(?:json)?", "", response).strip()
            cleaned = cleaned.replace("```", "").strip()
            
            # Try to find JSON object
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(0)
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Response: {response[:500]}...")
            return {}
    
    def _save_to_history(self, summary: str):
        """Save conversation to chat history"""
        try:
            self.session_messages.add_user_message(self.user_query)
            self.session_messages.add_ai_message(summary)
            
            # Also save full iteration context
            self.cache.set_org_data(
                f"travel_plan_{datetime.now().timestamp()}",
                {
                    'query': self.user_query,
                    'iterations': [it.to_dict() for it in self.iterations],
                    'extracted_info': self.extracted_info
                },
                self.session_id
            )
        except Exception as e:
            print(f"⚠️ Failed to save to history: {e}")
    
    def _save_execution_metadata(self):
        """Save execution metadata for debugging/analytics"""
        try:
            metadata = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "date": current_date,
                "total_iterations": len(self.iterations),
                "total_api_calls": sum(
                    it.execution_summary['total_count'] 
                    for it in self.iterations
                ),
                "total_time": sum(
                    it.execution_summary['total_execution_time'] 
                    for it in self.iterations
                ),
                "progress_log": self.progress_log
            }
            
            self.cache.set_org_data(
                f"execution_metadata_{datetime.now().timestamp()}",
                metadata,
                self.session_id
            )
        except Exception as e:
            print(f"⚠️ Failed to save metadata: {e}")