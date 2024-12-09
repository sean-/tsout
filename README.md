# `tsout`

Timestamp stdout/stderr output with microsecond precision. Maintains proper ordering and handles partial line buffering.

## Features

- Microsecond-precision timestamps for both stdout and stderr
- Non-blocking I/O with proper partial line handling
- Preserves multi-line output spacing
- Color-coded output (disabled with the `-C` flag):
  - `stdout` in `white`
  - `stderr` in `yellow`
  - Timestamps in default color
- Multiple timestamp formats:
  - Time since start (default)
  - Unix timestamps (`-T`)
  - UTC timestamps (`-u`)
- Optional file descriptor display (`-v`)
- Configurable delimiters (space or colon)

## Installation

```console
# Clone the repository
git clone https://github.com/yourusername/tsout.git

# Optional: Move to your path
sudo install -m 0755 tsout.py /usr/local/bin/tsout
```

## Usage

Basic usage:
```console
$ tsout command [args...]
```

Options:
```console
-T    Show Unix timestamps
-u    Show UTC timestamps
-v    Show file descriptor numbers
-C    Disable color output
-s    Use space as delimiter instead of colon
```

## Examples

Basic usage (time since start):
```console
$ tsout ./test.sh
0.000123: This is stdout line 1              # White
0.000234: This is stdout line 2              # White
1.001234: This is stderr line 1              # Yellow
1.001456: This is stderr line 2              # Yellow
2.002345: This is stdout after 1 second      # White
2.502345: This is an incomplete line that continues here
```

With file descriptors and space delimiter:
```console
$ tsout -v -s ./test.sh
1 0.000123 This is stdout line 1             # fd 1 = stdout (White)
1 0.000234 This is stdout line 2             # fd 1 = stdout (White)
2 1.001234 This is stderr line 1             # fd 2 = stderr (Yellow)
2 1.001456 This is stderr line 2             # fd 2 = stderr (Yellow)
```

With UTC timestamps:
```console
$ tsout -u -C ./test.sh
2024-12-09 19:56:26.250222: This is stdout line 1
2024-12-09 19:56:26.250222: This is stdout line 2
2024-12-09 19:56:27.264228: This is stderr line 1
2024-12-09 19:56:27.264228: This is stderr line 2
2024-12-09 19:56:28.294530: This is stdout after 1 second
2024-12-09 19:56:28.835372: This is an incomplete line that continues here
2024-12-09 19:56:29.920876: 1. multi-line
2024-12-09 19:56:29.920876: 2. line2
2024-12-09 19:56:29.920876: 3. line3
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
