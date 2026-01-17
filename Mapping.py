from collections import deque

def solve(grid, start, end):
    queue = deque( )
    visited = {start}
    parent = {start: None}

    while queue:
        x, y = queue.popleft()
        if (x, y) == end:
            path = []
            curr = end
            while curr != start:
                path.append(curr)
                curr = parent path.append(start)
            return path[::-1 (x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
            if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) \
               and grid  == 1 and (nx,ny) not in visited:
                visited.add((nx,ny))
                queue.append((nx,ny))
                parent = (x,y)
    return None  # no path
