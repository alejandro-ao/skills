#!/usr/bin/env python3
"""
Plot agent benchmark trends from JSONL results.

Usage:
    python3 plot-trends.py --input ~/.pi/agent/benchmarks/results.jsonl --model gpt-4o
    python3 plot-trends.py --input ~/.pi/agent/benchmarks/results.jsonl --task fix-login-bug
    python3 plot-trends.py --input ~/.pi/agent/benchmarks/results.jsonl --tag-prefix v2.3
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not installed. Install with: pip install matplotlib")


def load_results(path: str):
    """Load JSONL results file."""
    results = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def filter_results(results, model=None, task=None, tag_prefix=None):
    """Filter results by criteria."""
    filtered = []
    for r in results:
        # Filter by model: keep runs that tested this model
        if model:
            model_results = [m for m in r.get('results', []) if m['model'] == model]
            if not model_results:
                continue
            # Replace results with just this model's data
            r = {**r, 'results': model_results}
        
        # Filter by task slug
        if task and r.get('task_slug') != task:
            continue
        
        # Filter by tag prefix
        if tag_prefix and not r.get('tag', '').startswith(tag_prefix):
            continue
        
        filtered.append(r)
    
    return filtered


def extract_trends(results):
    """Extract time-series data per model."""
    trends = defaultdict(list)
    
    for r in sorted(results, key=lambda x: x['timestamp']):
        ts = datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00'))
        tag = r.get('tag', r['timestamp'])
        
        for model_result in r.get('results', []):
            model = model_result['model']
            overall = model_result['scores']['overall']
            
            trends[model].append({
                'timestamp': ts,
                'tag': tag,
                'overall': overall,
                'correctness': model_result['scores']['correctness'],
                'efficiency': model_result['scores']['efficiency'],
                'tool_use': model_result['scores']['tool_use'],
                'verification': model_result['scores']['verification'],
            })
    
    return trends


def plot_trends(trends, output_path, title="Benchmark Trends"):
    """Plot trends using matplotlib."""
    if not MATPLOTLIB_AVAILABLE:
        print("Cannot plot: matplotlib not available")
        return
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    dimensions = ['overall', 'correctness', 'efficiency', 'tool_use', 'verification']
    dim_labels = ['Overall', 'Correctness', 'Efficiency', 'Tool Use', 'Verification']
    colors = plt.cm.tab10.colors
    
    for idx, (dim, label) in enumerate(zip(dimensions, dim_labels)):
        ax = axes[idx // 3, idx % 3]
        
        for i, (model, data) in enumerate(trends.items()):
            times = [d['timestamp'] for d in data]
            scores = [d[dim] for d in data]
            ax.plot(times, scores, marker='o', label=model, color=colors[i % 10])
        
        ax.set_ylim(0, 1.05)
        ax.set_ylabel('Score')
        ax.set_title(label)
        ax.legend(loc='lower right', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Summary table in the last subplot
    ax = axes[1, 2]
    ax.axis('off')
    
    # Build summary text
    summary_lines = ["Latest Scores:\n"]
    for model, data in trends.items():
        if data:
            latest = data[-1]
            summary_lines.append(
                f"{model}: {latest['overall']:.2f} "
                f"(C:{latest['correctness']:.2f} "
                f"E:{latest['efficiency']:.2f} "
                f"T:{latest['tool_use']:.2f} "
                f"V:{latest['verification']:.2f})"
            )
    
    ax.text(0.1, 0.5, '\n'.join(summary_lines), 
            transform=ax.transAxes, fontsize=10, 
            verticalalignment='center', family='monospace')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")


def print_text_trends(trends):
    """Print trends as text when matplotlib unavailable."""
    for model, data in trends.items():
        print(f"\n{'='*60}")
        print(f"Model: {model}")
        print(f"{'='*60}")
        
        scores = [d['overall'] for d in data]
        if len(scores) >= 2:
            delta = scores[-1] - scores[-2]
            arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
            print(f"Latest: {scores[-1]:.2f} ({arrow} {delta:+.2f} vs previous)")
        else:
            print(f"Latest: {scores[-1]:.2f}")
        
        print(f"\nHistory:")
        for d in data:
            tag = d['tag'][:20] if len(d['tag']) > 20 else d['tag']
            print(f"  {d['timestamp'].strftime('%Y-%m-%d %H:%M')} | "
                  f"{d['overall']:.2f} | {tag}")


def main():
    parser = argparse.ArgumentParser(description='Plot agent benchmark trends')
    parser.add_argument('--input', required=True, help='Path to results.jsonl')
    parser.add_argument('--output', default='trends.png', help='Output image path')
    parser.add_argument('--model', help='Filter by model name')
    parser.add_argument('--task', help='Filter by task slug')
    parser.add_argument('--tag-prefix', help='Filter by tag prefix')
    args = parser.parse_args()
    
    results = load_results(args.input)
    filtered = filter_results(results, args.model, args.task, args.tag_prefix)
    
    if not filtered:
        print("No results match the given filters.")
        return
    
    trends = extract_trends(filtered)
    
    if MATPLOTLIB_AVAILABLE:
        title_parts = []
        if args.model:
            title_parts.append(f"Model: {args.model}")
        if args.task:
            title_parts.append(f"Task: {args.task}")
        if args.tag_prefix:
            title_parts.append(f"Tag: {args.tag_prefix}*")
        
        title = "Benchmark Trends" + (" — " + ", ".join(title_parts) if title_parts else "")
        plot_trends(trends, args.output, title)
    else:
        print_text_trends(trends)


if __name__ == '__main__':
    main()
