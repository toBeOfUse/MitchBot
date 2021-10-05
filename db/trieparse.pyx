#cython: language_level=3
# distutils: sources = ./src/trieparse.c
# distutils: include_dirs = ./src/

cdef extern from "./src/trieparse.h":
    const char* search_words(const char* trie_buffer, const char* eligible_characters)

cpdef search(bytes trie_buffer, bytes eligible_characters):
    cdef char * result = search_words(<bytes>trie_buffer, eligible_characters)
    return <bytes> result
