import json
from Agents import CodeGenerationAgents
from intent_tree_generator import IntentTreeGenerator
import datetime
import os

def test_function(index):
    pass
    # print(f"Index {index} is shouting: Hello World")

class fake_MAGS:
    def __init__(self, index):
        self.index = index
        self.turn_counter = 0
        # print(f"Agent {index} initialized")

    def run_conversation_turn(self, previous_execution_result=None):
        # print("Running a single turn of the conversation on thread ", self.index)
        # Save the conversation turn to a local file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create the directory if it doesn't exist
        os.makedirs("test", exist_ok=True)
        
        # Include turn number in filename to ensure different files for different turns
        self.turn_counter += 1
        filename = f"test/conversation_turn_{self.index}_turn{self.turn_counter}_{timestamp}.txt"
        
        with open(filename, "w") as f:
            f.write(f"Conversation turn from agent {self.index}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Turn number: {self.turn_counter}\n")
            f.write("Content: Running a single turn of the conversation")
        # print(f"Saved conversation to {filename}")
        return "One turn completed"
    
    def run_simulation(self, max_turns=2):
        # print("Running the simulation")
        for i in range(max_turns):
            # print(f"--- Turn {i + 1} ---")
            self.run_conversation_turn()
        return "Simulation completed"

class MultiAgentCodeGenSimulator:
    """
    Orchestrates interactions between the three agents to simulate a code generation dialog.
    Uses an intent tree generator to create task hierarchies based on the main task.
    """
    def __init__(self, main_task="写一个爬虫程序，爬取指定URL的微信文章内容并保存到本地", model="qwen-max-latest", dialog_save_dir="dialog_history", user_index=0):
        """
        Initialize the simulator with a main task.
        
        Args:
            main_task (str): The root task to decompose into a hierarchical tree
            model (str): The model to use for generating the intent tree
            dialog_save_dir (str): Directory to save dialog history
            user_index (int): User index for dialog tracking
        """


        # Generate intent tree based on main task
        tree_generator = IntentTreeGenerator(model=model)
        intent_tree = tree_generator.generate_intent_tree(main_task)
        
        # Initialize agents with the generated intent tree
        self.agents = CodeGenerationAgents(
            intent_tree=intent_tree,
            dialog_save_dir=dialog_save_dir,
            user_index=user_index
        )

    def run_conversation_turn(self, previous_execution_result=None):
        """
        Run a single turn of the conversation between the three agents
        
        Args:
            previous_execution_result: The execution result from the previous turn
        """
        # Step 1: Get user prompt (Agent 3)
        # Pass the previous execution result to the agent
        user_prompt = self.agents.agent3_novice_user(previous_execution_result)
        
        # Step 2: Get code response from Agent 1 (code generator)
        assistant_response = self.agents.agent1_code_generator(user_prompt)
        
        # Step 3: Get execution analysis (Agent 2)
        updated_intent_tree, execution_result = self.agents.agent2_execution_analyzer(assistant_response)
        
        # Return the current turn information for display purposes only
        return {
            "user_prompt": user_prompt,
            "assistant_response": assistant_response,
            "execution_result": execution_result,
            "updated_intent_tree": updated_intent_tree
        }
    
    def run_simulation(self, max_turns=20):
        """
        Run the simulation until all tasks are completed or max_turns is reached.
        """
        turn_count = 0
        all_tasks_completed = False
        current_execution_result = None  # Start with no execution result
        
        while turn_count < max_turns and not all_tasks_completed:
            # print(f"\n--- Turn {turn_count + 1} ---")
            
            # # print the current intent tree state before this turn
            # print(f"\nCurrent Intent Tree Status:")
            # print("-" * 40)
            # print(self.agents.intent_tree)
            # print("-" * 40)
            
            turn = self.run_conversation_turn(previous_execution_result=current_execution_result)
            
            # Update the execution result for the next turn
            current_execution_result = turn['execution_result']

            # print(f"User: {turn['user_prompt']}")
            # print(f"\nAssistant:\n{turn['assistant_response']}")
            # print(f"\nExecution Analysis:\n{turn['execution_result']}")
            
            # # print the updated intent tree after this turn
            # print(f"\nUpdated Intent Tree Status:")
            # print("-" * 40)
            # print(self.agents.intent_tree)
            # print("-" * 40)
            
            # print("\n" + "=" * 80)

            # Check for completion by analyzing the updated intent tree for [COMPLETED] markers
            updated_intent = turn['updated_intent_tree']
            all_tasks_completed = self._check_all_tasks_completed(updated_intent)
            
            turn_count += 1
            
        if all_tasks_completed:
            pass
            # print("\nSimulation complete! All tasks have been completed.")
        else:
            pass
            # print(f"\nSimulation reached maximum turns ({max_turns}) without completing all tasks.")
        
        # Save dialog history from the agents
        dialog_data = self.agents.access_dialog_history()
        return dialog_data
    
    def _check_all_tasks_completed(self, updated_intent_tree_str):
        """Check if all tasks are marked as completed in the updated intent tree"""
        # A simple heuristic: check if there are any [NOT COMPLETED] markers in the string
        return "[NOT COMPLETED]" not in updated_intent_tree_str


# Example usage
if __name__ == "__main__":
    # Create a simulator with a specific task
    main_task = "写一个爬虫程序，爬取指定URL的内容并保存到本地"
    simulator = MultiAgentCodeGenSimulator(main_task=main_task)
    
    # Run the simulation
    dialog_data = simulator.run_simulation(max_turns=20)
    
    # Dialog data is already saved by the agents.access_dialog_history() call
    # print(f"\nDialog saved to {dialog_data['dialog_file'] if 'dialog_file' in dialog_data else 'the configured directory'}")

    # # Create a fake_MAGS instance and run a conversation turn
    # agent = fake_MAGS(1)
    # result = agent.run_simulation()
    # # print(result)