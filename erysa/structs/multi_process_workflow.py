from multiprocessing import Manager, Pool, cpu_count
from typing import Sequence, Union, Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from swarms.structs.agent import Agent
from swarms.structs.base_workflow import BaseWorkflow
from swarms.utils.loguru_logger import initialize_logger

logger = initialize_logger(log_folder="multi_process_workflow")


class MultiProcessWorkflow(BaseWorkflow):
    """
    Initialize a MultiProcessWorkflow object.

    Args:
        max_workers (int): The maximum number of workers to use for parallel processing.
        autosave (bool): Flag indicating whether to automatically save the workflow.
        agents (List[Union[Agent, Callable]]): A list of Agent objects or callable functions representing the workflow tasks.
        *args: Additional positional arguments.
        **kwargs: Additional keyword arguments.

    Example:
    >>> from swarms.structs.multi_process_workflow import MultiProcessingWorkflow
    >>> from swarms.structs.task import Task
    >>> from datetime import datetime
    >>> from time import sleep
    >>>
    >>> # Define a simple task
    >>> def simple_task():
    >>>     sleep(1)
    >>>     return datetime.now()
    >>>
    >>> # Create a task object
    >>> task = Task(
    >>>     name="Simple Task",
    >>>     execute=simple_task,
    >>>     priority=1,
    >>> )
    >>>
    >>> # Create a workflow with the task
    >>> workflow = MultiProcessingWorkflow(tasks=[task])
    >>>
    >>> # Run the workflow
    >>> results = workflow.run(task)
    >>>
    >>> # Print the results
    >>> print(results)
    """

    def __init__(
        self,
        max_workers: int = 5,
        autosave: bool = True,
        agents: Sequence[Union[Agent, Callable]] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.max_workers = max_workers
        self.autosave = autosave
        self.agents = agents

        self.max_workers or cpu_count()

        # Log
        logger.info(
            (
                "Initialized MultiProcessWorkflow with"
                f" {self.max_workers} max workers and autosave set to"
                f" {self.autosave}"
            ),
        )

        # Log the agents
        if self.agents is not None:
            for agent in self.agents:
                logger.info(f"Agent: {agent.agent_name}")

    def execute_task(self, task: str, *args, **kwargs):
        """Execute a task and handle exceptions.

        Args:
            task (Task): The task to execute.
            *args: Additional positional arguments for the task execution.
            **kwargs: Additional keyword arguments for the task execution.

        Returns:
            Any: The result of the task execution.

        """
        try:
            if self.agents is not None:
                # Execute the task
                for agent in self.agents:
                    result = agent.run(task, *args, **kwargs)

            return result

        except Exception as e:
            logger.error(
                (
                    "An error occurred during execution of task"
                    f" {task}: {str(e)}"
                ),
            )
            return None

    def run(self, task: str, *args, **kwargs):
        """Run the workflow.

        Args:
            task (Task): The task to run.
            *args: Additional positional arguments for the task execution.
            **kwargs: Additional keyword arguments for the task execution.

        Returns:
            List[Any]: The results of all executed tasks.

        """
        try:
            results = []
            with Manager() as manager:
                with Pool(
                    processes=self.max_workers, *args, **kwargs
                ) as pool:
                    # Using manager.list() to collect results in a process safe way
                    results_list = manager.list()
                    jobs = [
                        pool.apply_async(
                            self.execute_task,  # Pass the function, not the function call
                            args=(task,)
                            + args,  # Pass the arguments as a tuple
                            kwds=kwargs,  # Pass the keyword arguments as a dictionary
                            callback=results_list.append,
                            timeout=task.timeout,
                        )
                        for agent in self.agents
                    ]

                    # Wait for all jobs to complete
                    for job in jobs:
                        job.get()

                    results = list(results_list)

                return results
        except Exception as error:
            logger.error(f"Error in run: {error}")
            return None

    async def async_run(self, task: str, *args, **kwargs):
        """Asynchronously run the workflow.

        Args:
            task (Task): The task to run.
            *args: Additional positional arguments for the task execution.
            **kwargs: Additional keyword arguments for the task execution.

        Returns:
            List[Any]: The results of all executed tasks.

        """
        try:
            results = []
            with ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                futures = [
                    executor.submit(
                        self.execute_task, task, *args, **kwargs
                    )
                    for _ in range(len(self.agents))
                ]
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

            return results
        except Exception as error:
            logger.error(f"Error in async_run: {error}")
            return None

    def batched_run(
        self, tasks: List[str], batch_size: int = 5, *args, **kwargs
    ):
        """Run tasks in batches.

        Args:
            tasks (List[str]): A list of tasks to run.
            batch_size (int): The size of each batch.
            *args: Additional positional arguments for the task execution.
            **kwargs: Additional keyword arguments for the task execution.

        Returns:
            List[Any]: The results of all executed tasks.

        """
        try:
            results = []
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i : i + batch_size]
                with Pool(processes=self.max_workers) as pool:
                    results_list = pool.map(
                        self.execute_task, batch, *args, **kwargs
                    )
                    results.extend(results_list)

            return results
        except Exception as error:
            logger.error(f"Error in batched_run: {error}")
            return None

    def concurrent_run(self, tasks: List[str], *args, **kwargs):
        """Run tasks concurrently.

        Args:
            tasks (List[str]): A list of tasks to run.
            *args: Additional positional arguments for the task execution.
            **kwargs: Additional keyword arguments for the task execution.

        Returns:
            List[Any]: The results of all executed tasks.

        """
        try:
            results = []
            with ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                futures = [
                    executor.submit(
                        self.execute_task, task, *args, **kwargs
                    )
                    for task in tasks
                ]
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

            return results
        except Exception as error:
            logger.error(f"Error in concurrent_run: {error}")
            return None
