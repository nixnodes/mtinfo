

def arg_parse_common(parser):
    parser.add_argument('-d', action = 'store_true', help = "Debug mode")
    parser.add_argument('-f', type = str, nargs = '?', help = 'Format output')
    parser.add_argument('-b', type = str, nargs = '?', help = 'Batch file')
    parser.add_argument('-config', type = str, nargs = '?', help = 'Config file')
    parser.add_argument('-list', action = 'store_true', help = 'List cache')
    parser.add_argument('-test', action = 'store_true', help = 'Run tests')
    parser.add_argument('-sort', type = str, nargs = '?', help = '')
    parser.add_argument('-order', type = str, nargs = '?', help = '')
    parser.add_argument('--cache', type = str, nargs = '?', help = 'Cache sqlite3 database')
    parser.add_argument('--cache_expire', type = int, nargs = '?', help = 'Cache expiration time')
    parser.add_argument('--rate_limit', type = str, nargs = '?', help = 'Query rate limit')
    parser.add_argument('--machine', action = 'store_true', help = 'Machine-readable output')
    parser.add_argument('query', nargs = '*')
