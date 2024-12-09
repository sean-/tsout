#!/usr/bin/env python3
"""
tsout: Timestamp stdout/stderr output with microsecond precision.

Captures and timestamps output from a command, maintaining proper ordering of stdout/stderr
and handling partial line buffering. Preserves multi-line output spacing.

Features:
- Timestamps both stdout and stderr with microsecond precision
- Non-blocking I/O with proper partial line buffering
- Colored output (white for stdout, yellow for stderr, or -C to disable)
- Unix timestamps (-T) or time since start
- UTC timestamps (-u) in human readable format
- Optional file descriptor display (-v)
- Space-delimited (-s) or colon-delimited output

Examples:
    # Basic usage - time since start
    tsout command arg1 arg2
    0.123456: output line

    # Show Unix timestamps
    tsout -T command
    1733768011.123456: output line

    # Show UTC timestamps
    tsout -u command
    2024-12-09 14:23:31.123456: output line

    # Show FDs and space-delimited
    tsout -v -s command
    1 0.123456 stdout line
    2 0.123789 stderr line

    See test.sh for sample output to exercise this code.
"""

import os
import sys
import time
import fcntl
import select
import signal
import argparse
import termios
import pty
from datetime import datetime, timezone

def set_non_blocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def run_with_ptys(cmd, use_unix_timestamps=False, use_utc=False, verbose=False, color=True, space_delim=False):
    stdout_parent, stdout_child = pty.openpty()
    stderr_parent, stderr_child = pty.openpty()

    if os.isatty(sys.stdin.fileno()):
        old_settings = termios.tcgetattr(sys.stdin.fileno())

    COLOR = {
        stdout_parent: '\033[1;97m',  # Bold Bright White for stdout
        stderr_parent: '\033[1;93m',  # Bold Bright Yellow for stderr
    }
    FD_MAP = {
        stdout_parent: sys.stdout.fileno(),
        stderr_parent: sys.stderr.fileno(),
    }
    RESET = '\033[0m'

    def format_timestamp(ts):
        if use_utc:
            return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
        elif use_unix_timestamps:
            return f"{ts:.6f}"
        else:
            return f"{ts - start_time:.6f}"

    def format_prefix(fd, timestamp, color_map, fd_map, reset_code, color_enabled=True, verbose=False, space_delim=False):
        parts = []
        if color_enabled:
            parts.append(str(color_map[fd]))

        if verbose:
            parts.append(str(fd_map[fd]))
            parts.append(' ' if space_delim else '@')

        parts.append(format_timestamp(timestamp))
        parts.append(' ' if space_delim else ': ')

        if color_enabled:
            parts.append(reset_code)

        return ''.join(parts).encode()

    try:
        pid = os.fork()
        if pid == 0:  # Child
            os.close(stdout_parent)
            os.close(stderr_parent)
            os.setsid()

            os.dup2(stdout_child, sys.stdout.fileno())
            os.dup2(stderr_child, sys.stderr.fileno())

            if stdout_child > 2:
                os.close(stdout_child)
            if stderr_child > 2:
                os.close(stderr_child)

            if not color:
                os.environ['TERM'] = 'dumb'
            os.execvp(cmd[0], cmd)
            os._exit(1)

        else:  # Parent
            os.close(stdout_child)
            os.close(stderr_child)

            set_non_blocking(stdout_parent)
            set_non_blocking(stderr_parent)

            start_time = time.time()
            buffers = {
                stdout_parent: b'',
                stderr_parent: b'',
            }

            # Track whether we are currently in a line for each FD
            line_in_progress = {
                stdout_parent: False,
                stderr_parent: False
            }

            fds = [stdout_parent, stderr_parent]

            while fds:
                try:
                    readable, _, _ = select.select(fds, [], [])

                    # Process stderr first, then stdout
                    for fd in sorted(readable, reverse=True):
                        try:
                            chunk = os.read(fd, 4096)
                            if not chunk:
                                fds.remove(fd)
                                os.close(fd)
                                continue

                            out = sys.stdout.buffer if fd == stdout_parent else sys.stderr.buffer
                            now = time.time()

                            buffers[fd] += chunk
                            lines = buffers[fd].split(b'\n')
                            # Every element in lines except possibly the last is a complete line
                            complete_lines = lines[:-1]
                            partial_line = lines[-1]

                            prefix = format_prefix(fd, now, COLOR, FD_MAP, RESET, color, verbose, space_delim)

                            # Print complete lines
                            for line in complete_lines:
                                if not line_in_progress[fd]:
                                    out.write(prefix)
                                out.write(line + b'\n')
                                line_in_progress[fd] = False

                            if partial_line:
                                out.write(prefix + partial_line)
                                line_in_progress[fd] = True
                                buffers[fd] = b''  # discard after printing
                            else:
                                buffers[fd] = b''  # no partial line, clear buffer

                            out.flush()

                        except OSError:
                            fds.remove(fd)
                            os.close(fd)

                except KeyboardInterrupt:
                    os.kill(pid, signal.SIGTERM)
                    sys.exit(130)

            # Wait for child to finish
            os.waitpid(pid, 0)

            # If there's leftover data after the child exits, print it with a newline
            for fd in buffers:
                if buffers[fd]:
                    out = sys.stdout.buffer if fd == stdout_parent else sys.stderr.buffer
                    now = time.time()
                    if not line_in_progress[fd]:
                        prefix = format_prefix(fd, now, COLOR, FD_MAP, RESET, color, verbose, space_delim)
                        out.write(prefix + buffers[fd] + b'\n')
                    else:
                        out.write(buffers[fd] + b'\n')
                    out.flush()

    finally:
        if os.isatty(sys.stdin.fileno()) and 'old_settings' in locals():
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Timestamp stdout/stderr output with microsecond precision'
    )
    parser.add_argument('-T', action='store_true', help='Show Unix timestamps')
    parser.add_argument('-u', action='store_true', help='Show UTC timestamps')
    parser.add_argument('-v', action='store_true', help='Show file descriptor numbers')
    parser.add_argument('-C', action='store_false', dest='color', help='Disable color output')
    parser.add_argument('-s', action='store_true', help='Use space as delimiter')
    args, remaining = parser.parse_known_args()

    if args.T and args.u:
        parser.error('Cannot use both -T and -u')

    if not remaining:
        parser.print_help()
        sys.exit(1)

    if '--' in remaining:
        cmd = remaining[remaining.index('--') + 1:]
    else:
        cmd = remaining

    run_with_ptys(cmd, args.T, args.u, args.v, args.color, args.s)
