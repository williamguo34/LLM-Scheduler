"""
Enhanced Gantt Chart for FJSP Scheduling
Provides professional, informative, and visually appealing scheduling presentations
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import random
import time
import os
from datetime import datetime, timedelta
import seaborn as sns
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.ticker as ticker

class EnhancedFJSPGanttChart:
    """
    Enhanced Gantt Chart class for FJSP scheduling with professional visualization
    """
    
    def __init__(self, total_n_jobs, number_of_machines, figsize=None, style='professional'):
        """
        Initialize the enhanced Gantt chart
        
        Args:
            total_n_jobs: Number of jobs
            number_of_machines: Number of machines
            figsize: Figure size tuple (width, height)
            style: Chart style ('professional', 'modern', 'minimal')
        """
        self.total_n_jobs = total_n_jobs
        self.number_of_machines = number_of_machines
        self.style = style
        self.operations_data = []
        self.machine_utilization = {}
        self.job_completion_times = {}
        self.makespan = 0
        
        # Set up the figure with appropriate size
        if figsize is None:
            figsize = (max(12, total_n_jobs * 1.2), max(8, number_of_machines * 1.5))
        
        self.fig, self.ax = plt.subplots(figsize=figsize)
        self._setup_style()
        self._initialize_chart()
        
    def _setup_style(self):
        """Setup the visual style based on the chosen theme"""
        if self.style == 'professional':
            plt.style.use('seaborn-v0_8-whitegrid')
            self.colors = self._generate_professional_colors()
            self.edge_color = 'black'
            self.edge_width = 0.5
        elif self.style == 'modern':
            plt.style.use('seaborn-v0_8-darkgrid')
            self.colors = self._generate_modern_colors()
            self.edge_color = 'white'
            self.edge_width = 1.0
        else:  # minimal
            plt.style.use('default')
            self.colors = self._generate_minimal_colors()
            self.edge_color = 'gray'
            self.edge_width = 0.3
            
    def _generate_professional_colors(self):
        """Generate professional color palette"""
        # Use a professional color scheme
        base_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
        ]
        
        # Extend colors if needed
        colors = []
        for i in range(self.total_n_jobs):
            colors.append(base_colors[i % len(base_colors)])
        return colors
    
    def _generate_modern_colors(self):
        """Generate modern color palette"""
        # Use vibrant, modern colors
        base_colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
            '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2'
        ]
        
        colors = []
        for i in range(self.total_n_jobs):
            colors.append(base_colors[i % len(base_colors)])
        return colors
    
    def _generate_minimal_colors(self):
        """Generate minimal color palette"""
        # Use subtle, minimal colors
        base_colors = [
            '#8B9DC3', '#A8DADC', '#F1FAEE', '#E63946', '#457B9D',
            '#1D3557', '#F77F00', '#FCBF49', '#D62828', '#023047'
        ]
        
        colors = []
        for i in range(self.total_n_jobs):
            colors.append(base_colors[i % len(base_colors)])
        return colors
    
    def _initialize_chart(self):
        """Initialize the chart with proper formatting"""
        # Set up the chart area with more space
        self.ax.set_xlim(0, 1)  # Will be updated as operations are added
        self.ax.set_ylim(-0.5, self.number_of_machines - 0.5)
        
        # Set machine labels with larger font
        machine_labels = [f'Machine {i+1}' for i in range(self.number_of_machines)]
        self.ax.set_yticks(range(self.number_of_machines))
        self.ax.set_yticklabels(machine_labels, fontsize=16, fontweight='bold')
        
        # Invert y-axis so Machine 1 is at the top
        self.ax.invert_yaxis()
        
        # Set labels and title with larger fonts
        self.ax.set_xlabel('Time', fontsize=18, fontweight='bold')
        self.ax.set_ylabel('Machines', fontsize=18, fontweight='bold')
        
        # Add grid for better readability
        self.ax.grid(True, alpha=0.3, linestyle='--')
        self.ax.set_axisbelow(True)
        
        # Set background color
        self.ax.set_facecolor('#f8f9fa')
        
        # Increase tick label sizes
        self.ax.tick_params(axis='both', which='major', labelsize=14)
        
    def add_operation(self, job, operation, machine, start_time, duration, 
                     job_name=None, operation_name=None, machine_name=None):
        """
        Add an operation to the Gantt chart
        
        Args:
            job: Job ID
            operation: Operation ID  
            machine: Machine ID
            start_time: Start time of the operation
            duration: Duration of the operation
            job_name: Optional job name
            operation_name: Optional operation name
            machine_name: Optional machine name
        """
        # Store operation data for statistics
        op_data = {
            'job': job,
            'operation': operation,
            'machine': machine,
            'start_time': start_time,
            'duration': duration,
            'end_time': start_time + duration,
            'job_name': job_name or f'Job {job+1}',
            'operation_name': operation_name or f'Op {operation+1}',
            'machine_name': machine_name or f'Machine {machine+1}'
        }
        self.operations_data.append(op_data)
        
        # Update makespan
        self.makespan = max(self.makespan, start_time + duration)
        
        # Update machine utilization
        if machine not in self.machine_utilization:
            self.machine_utilization[machine] = 0
        self.machine_utilization[machine] += duration
        
        # Update job completion times
        if job not in self.job_completion_times:
            self.job_completion_times[job] = 0
        self.job_completion_times[job] = max(self.job_completion_times[job], start_time + duration)
        
        # Draw the operation bar
        self._draw_operation_bar(op_data)
        
    def _draw_operation_bar(self, op_data):
        """Draw a single operation bar with enhanced styling"""
        job = op_data['job']
        operation = op_data['operation']
        machine = op_data['machine']
        start_time = op_data['start_time']
        duration = op_data['duration']
        
        # Get color for this job
        color = self.colors[job % len(self.colors)]
        
        # Create the bar with enhanced styling
        bar = Rectangle(
            (start_time, machine - 0.4), 
            duration, 
            0.8,
            facecolor=color,
            edgecolor=self.edge_color,
            linewidth=self.edge_width,
            alpha=0.8
        )
        self.ax.add_patch(bar)
        
        # Add operation label with better positioning
        label_x = start_time + duration * 0.1
        label_y = machine
        
        # Create a more informative label
        if duration > 0.5:  # Only add label if bar is wide enough
            label_text = f"J{job+1}\nO{operation+1}"
            if op_data['job_name'] != f'Job {job+1}':
                label_text = f"{op_data['job_name']}\nO{operation+1}"
            
            self.ax.text(
                label_x, label_y, label_text,
                fontsize=12, fontweight='bold',
                ha='left', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, edgecolor='gray', linewidth=1)
            )
        
        # Add duration text if bar is wide enough
        if duration > 1.0:
            duration_text = f"{duration:.1f}"
            self.ax.text(
                start_time + duration/2, machine,
                duration_text,
                fontsize=11, ha='center', va='center',
                color='white', fontweight='bold'
            )
    
    def add_statistics_panel(self):
        """Add a statistics panel to the chart"""
        # Calculate statistics
        total_operations = len(self.operations_data)
        avg_machine_utilization = np.mean(list(self.machine_utilization.values())) if self.machine_utilization else 0
        max_machine_utilization = max(self.machine_utilization.values()) if self.machine_utilization else 0
        
        # Create statistics text
        stats_text = f"""
        Scheduling Statistics:
        • Total Operations: {total_operations}
        • Makespan: {self.makespan:.2f}
        • Avg Machine Utilization: {avg_machine_utilization:.2f}
        • Max Machine Utilization: {max_machine_utilization:.2f}
        • Jobs Completed: {len(self.job_completion_times)}
        """
        
        # Position statistics box in the bottom right corner to avoid overlap with chart content
        self.ax.text(
            0.98, 0.02, stats_text,
            transform=self.ax.transAxes,
            fontsize=12,
            verticalalignment='bottom',
            horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.9, edgecolor='navy', linewidth=1)
        )
    
    def add_machine_utilization_bars(self):
        """Add machine utilization visualization - positioned to avoid overlap"""
        if not self.machine_utilization:
            return
            
        # Create a second y-axis for utilization positioned to avoid overlap
        ax2 = self.ax.twinx()
        machines = list(self.machine_utilization.keys())
        utilizations = list(self.machine_utilization.values())
        
        # Position utilization bars to the right side with better spacing
        bars = ax2.barh(machines, utilizations, alpha=0.3, color='red', label='Utilization', height=0.2)
        ax2.set_ylabel('Machine Utilization', color='red', fontsize=12, fontweight='bold')
        ax2.tick_params(axis='y', labelcolor='red', labelsize=10)
        
        # Position utilization values to avoid overlap with main chart
        for i, (machine, util) in enumerate(zip(machines, utilizations)):
            # Position text to the right of the chart area
            ax2.text(util + max(utilizations) * 0.1, machine, f'{util:.1f}', 
                    va='center', color='red', fontweight='bold', fontsize=9)
    
    def add_timeline_markers(self):
        """Add timeline markers for better time reference"""
        if self.makespan == 0:
            return
            
        # Add vertical lines at regular intervals
        max_time = self.makespan
        interval = max(1, max_time // 10)  # 10 intervals
        
        for t in range(0, int(max_time) + 1, int(interval)):
            self.ax.axvline(x=t, color='gray', linestyle=':', alpha=0.5, linewidth=1)
            self.ax.text(t, -0.3, f'{t}', ha='center', va='top', fontsize=12, color='gray', fontweight='bold')
    
    def finalize_chart(self, title=None, save_path=None, show_legend=True, 
                      show_statistics=True, show_utilization=False, show_timeline=True):
        """
        Finalize the chart with all enhancements
        
        Args:
            title: Chart title
            save_path: Path to save the chart
            show_legend: Whether to show legend
            show_statistics: Whether to show statistics panel
            show_utilization: Whether to show machine utilization
            show_timeline: Whether to show timeline markers
        """
        # Update x-axis limits with more space
        self.ax.set_xlim(0, self.makespan * 1.15)
        
        # Add timeline markers
        if show_timeline:
            self.add_timeline_markers()
        
        # Add statistics panel
        if show_statistics:
            self.add_statistics_panel()
        
        # Add machine utilization
        if show_utilization:
            self.add_machine_utilization_bars()
        
        # Add legend
        if show_legend:
            self._add_legend()
        
        # Set title with larger font
        if title:
            self.ax.set_title(title, fontsize=20, fontweight='bold', pad=30)
        else:
            self.ax.set_title(f'FJSP Schedule - Makespan: {self.makespan:.2f}', 
                            fontsize=20, fontweight='bold', pad=30)
        
        # Improve layout with more padding and better spacing
        # Extend x-axis to provide more space for utilization bars
        self.ax.set_xlim(0, self.makespan * 1.2)
        plt.tight_layout(pad=4.0)
        
        # Save if path provided
        if save_path:
            self.save_chart(save_path)
    
    def _add_legend(self):
        """Add a legend for job colors"""
        legend_elements = []
        for i in range(min(self.total_n_jobs, 10)):  # Limit legend to 10 items
            legend_elements.append(
                patches.Patch(color=self.colors[i], label=f'Job {i+1}')
            )
        
        if self.total_n_jobs > 10:
            legend_elements.append(
                patches.Patch(color='gray', label=f'... and {self.total_n_jobs - 10} more jobs')
            )
        
        self.ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98), 
                      fontsize=12, framealpha=0.9, edgecolor='black')
    
    def save_chart(self, filepath, dpi=300, format='png'):
        """
        Save the chart to file
        
        Args:
            filepath: Path to save the file
            dpi: Resolution for raster formats
            format: File format ('png', 'svg', 'pdf', 'jpg')
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save with high quality
        self.fig.savefig(
            filepath, 
            format=format,
            dpi=dpi,
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none'
        )
        print(f"Chart saved to: {filepath}")
    
    def get_statistics(self):
        """Get detailed scheduling statistics"""
        if not self.operations_data:
            return {}
        
        stats = {
            'total_operations': len(self.operations_data),
            'makespan': self.makespan,
            'machine_utilization': dict(self.machine_utilization),
            'job_completion_times': dict(self.job_completion_times),
            'avg_machine_utilization': np.mean(list(self.machine_utilization.values())) if self.machine_utilization else 0,
            'max_machine_utilization': max(self.machine_utilization.values()) if self.machine_utilization else 0,
            'min_machine_utilization': min(self.machine_utilization.values()) if self.machine_utilization else 0,
            'total_jobs': len(self.job_completion_times)
        }
        
        return stats
    
    def close(self):
        """Close the figure to free memory"""
        plt.close(self.fig)


# Compatibility wrapper for existing code
class DFJSP_GANTT_CHART(EnhancedFJSPGanttChart):
    """
    Compatibility wrapper for the original DFJSP_GANTT_CHART class
    """
    
    def __init__(self, total_n_job, number_of_machines):
        super().__init__(total_n_job, number_of_machines)
        self.total_n_job = total_n_job  # Keep original attribute name
        self.number_of_machines = number_of_machines
    
    def gantt_plt(self, job, operation, mach_a, start_time, dur_a, number_of_jobs):
        """
        Compatibility method for the original gantt_plt function
        """
        self.add_operation(
            job=job,
            operation=operation, 
            machine=mach_a,
            start_time=start_time,
            duration=dur_a
        )
    
    def initialize_plt(self):
        """Compatibility method - initialization is now done in __init__"""
        pass
    
    def colour_gen(self, n):
        """Compatibility method - colors are now generated in __init__"""
        return self.colors[:n]
