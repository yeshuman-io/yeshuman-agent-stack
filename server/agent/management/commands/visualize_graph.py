"""
Management command to visualize the response graph.
"""
import os
import asyncio
import logging
from django.core.management.base import BaseCommand

# Configure logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Command to visualize the response graph using LangGraph's built-in visualization.
    """
    help = "Visualize the response graph and save it to a file"

    def add_arguments(self, parser):
        """
        Add command line arguments.
        
        Args:
            parser: The argument parser
        """
        parser.add_argument(
            "--output",
            "-o",
            default="response_graph.png",
            help="Path where the graph image will be saved",
        )
        parser.add_argument(
            "--format",
            "-f",
            choices=["png", "md"],
            default="png",
            help="Output format (png or md for Mermaid markdown)",
        )

    async def visualize_graph(self, graph, output_path, title="BookedAI Response Graph"):
        """
        Generate and save a visualization of a LangGraph StateGraph.
        
        Args:
            graph: The StateGraph to visualize
            output_path: Path where the graph image will be saved
            title: Title to add to the visualization (for markdown output)
        """
        try:
            # Ensure the directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Determine the visualization method based on file extension
            if output_path.endswith(".png"):
                # Use Mermaid.Ink API for PNG generation
                from langchain_core.runnables.graph import MermaidDrawMethod
                
                # Get the graph visualization as PNG
                graph.get_graph().draw_mermaid_png(
                    draw_method=MermaidDrawMethod.API,
                    output_file_path=output_path
                )
                
                logger.info(f"Graph visualization saved to {output_path}")
            elif output_path.endswith(".md"):
                # Save as Mermaid markdown
                with open(output_path, "w") as f:
                    if title:
                        f.write(f"# {title}\n\n")
                    f.write("```mermaid\n")
                    f.write(graph.get_graph().draw_mermaid())
                    f.write("\n```")
                logger.info(f"Graph visualization saved as Mermaid markdown to {output_path}")
            else:
                logger.warning(f"Unsupported file extension. Using PNG format.")
                # Default to PNG using Mermaid.Ink
                from langchain_core.runnables.graph import MermaidDrawMethod
                graph.get_graph().draw_mermaid_png(
                    draw_method=MermaidDrawMethod.API,
                    output_file_path=f"{os.path.splitext(output_path)[0]}.png"
                )
                logger.info(f"Graph visualization saved to {os.path.splitext(output_path)[0]}.png")
                
        except Exception as e:
            logger.error(f"Error generating graph visualization: {e}")

    async def handle_async(self, *args, **options):
        """
        Execute the command asynchronously.
        
        Args:
            *args: Positional arguments
            **options: Named arguments
        """
        output_path = options["output"]
        output_format = options["format"]
        
        # Ensure the file extension matches the format
        if output_format == "md" and not output_path.endswith(".md"):
            output_path = f"{os.path.splitext(output_path)[0]}.md"
        elif output_format == "png" and not output_path.endswith(".png"):
            output_path = f"{os.path.splitext(output_path)[0]}.png"
        
        self.stdout.write(f"Generating graph visualization to {output_path}...")
        
        # Import here to avoid circular imports
        from agent.services import create_response_graph
        
        # Create the response graph
        graph = await create_response_graph()
        
        # Visualize the graph
        await self.visualize_graph(graph, output_path)
        
        self.stdout.write(self.style.SUCCESS(f"Graph visualization saved to {output_path}"))

    def handle(self, *args, **options):
        """
        Execute the command.
        
        Args:
            *args: Positional arguments
            **options: Named arguments
        """
        import asyncio
        
        # Run the async function
        asyncio.run(self.handle_async(*args, **options)) 