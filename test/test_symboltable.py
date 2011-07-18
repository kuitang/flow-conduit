import test_bootstrap
import symboltable
st = symboltable.SymbolTable(map={'st.a':1})
schild = st.new_child({'schild.b':2})
print st['st.a']
print schild['schild.b']
print schild
print st
print schild.parents

