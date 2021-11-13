#cython: language_level=3
# distutils: sources = ./src/trieparse.c
# distutils: include_dirs = ./src/

cdef extern from "./src/trieparse.h":
    const char* search_words(const char* trie_buffer, const char* eligible_characters)
    int is_word_in_it(const char* trie_buffer, const char* word, int word_length)

cpdef search(bytes trie_buffer, bytes eligible_characters):
    cdef const char * result = search_words(<bytes>trie_buffer, eligible_characters)
    return <bytes> result

cpdef is_word_there(bytes trie_buffer, bytes word):
    cdef int result = is_word_in_it(trie_buffer, word, len(word))
    return <bint> result
