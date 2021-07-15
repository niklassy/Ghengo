from core.constants import Languages

NEGATIONS = {
    Languages.DE: ['kein', 'nicht'],
    Languages.EN: ['not', 'no'],
}

NUM_END_VARIATIONS = {
    Languages.DE: ['ßig', 'zig']
}

LIKE_NUM_WORDS = {
    Languages.DE: {
        'eins': 1,
        'zwei': 2,
        'drei': 3,
        'vier': 4,
        'fünf': 5,
        'sechs': 6,
        'sieben': 7,
        'acht': 8,
        'neun': 9,
        'zehn': 10,
        'elf': 11,
        'zwölf': 12,
        'dreizehn': 13,
        'zwanzig': 13,
        'hundert': 100,
    }
}

FILE_EXTENSIONS = {
    # text
    'docx': 'Word',
    'log': 'Log',
    'txt': 'Text',
    'tex': 'LaTex',

    # data
    'csv': 'CSV',
    'pptx': 'PowerPoint',
    'xml': 'XML',

    # audio
    'mp3': 'MP3',
    'wav': 'Wave',

    # video
    'mov': 'Quicktime',
    'mp4': 'MP4',
    'wmv': 'Windows Video',

    # image
    'svg': 'Vector',
    'jpg': 'JPEG',
    'png': 'Image',
    'gif': 'GIF',
    'psd': 'Photoshop',
    'ai': 'Illustrator',

    # page layout
    'pdf': 'PDF',
    'indd': 'InDesign',

    # spreadsheet
    'xlsx': 'Excel',

    # programming
    'js': 'JavaScript',
    'jsx': 'JavaScript React',
    'ts': 'TypeScript',
    'tsx': 'TypeScript React',
    'html': 'HTML',
    'css': 'CSS',
    'scss': 'SCSS',
    'py': 'Python',
    'json': 'JSON',
    'md': 'Markdown',
    'swift': 'Swift',
    'c': 'C',
    'cpp': 'C++',
    'sh': 'Bash',

    # compressed files
    'zip': 'Zip',
    '7z': '7-Zip',
    'tar.gz': 'Tarball',
}
