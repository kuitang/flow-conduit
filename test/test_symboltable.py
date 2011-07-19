import test_bootstrap
import symboltable

# For Python 2.6 (coding on Mac)
import unittest2

class TestSymbolTable(unittest2.TestCase):
    def setUp(self):
        self.st_map = {'st.a':1}
        self.st = symboltable.SymbolTable(map=self.st_map)

    def test_init(self):
        self.assertEquals(self.st.map, self.st_map)

    def test_init_with_parents(self):
        st2_map = {'st2.a':1}
        st2 = symboltable.SymbolTable(parents=(self.st,), map=st2_map)
        self.assertEquals(st2.map, st2_map)
        self.assertIn(self.st, st2._parents)

    def test_new_child(self):
        d = {'st2.b':2}
        st2 = self.st.new_child(d)
        self.assertEquals(d, st2.map)
        self.assertIn(self.st, st2._parents)

    def test_maps(self):
        st2 = symboltable.SymbolTable(map={'st2.b':2})
        self.assertIn(st2.map, list(st2.maps()))
        self.assertEquals([st2.map], list(st2.maps()))
        st3 = symboltable.SymbolTable(map={'st3.b':3})
        schild = symboltable.SymbolTable(parents=(self.st, st2, st3))
        schild_maps_list = list(schild.maps())        
        maps = [ self.st.map, st2.map, st3.map, schild.map ]
        for m in maps: self.assertIn(m, schild_maps_list)
        # No duplicates or extraneous
        self.assertEquals(len(maps), len(schild_maps_list))

        schild2 = schild.new_child({'schild2.a':20})
        schild2_maps_list = list(schild2.maps())
        for m in maps: self.assertIn(m, schild2_maps_list)
        self.assertIn(schild2.map, schild2_maps_list)
        self.assertEquals(len(maps) + 1, len(schild2_maps_list))

    def test_getitem(self):
        self.assertEquals(self.st_map['st.a'], self.st['st.a'])
        st2 = self.st.new_child(map={'st2.b':2, 'st2.c':3})
        self.assertEquals(st2['st.a'], self.st['st.a'])
        self.assertEquals(st2['st2.b'], 2)
        self.assertEquals(st2['st2.c'], 3)
    
    def test_keyerror(self):
        with self.assertRaises(KeyError): self.st['does-not-exist']
        st2 = self.st.new_child(map={'st2.b':2})
        with self.assertRaises(KeyError): st2['does-not-exist']

class TestWrappers(unittest2.TestCase):
    def setUp(s): 
        s.id_scalar     = lambda a: a
        s.id_none       = lambda: None
        s.id_pos        = lambda a,b,c: (a,b,c)
        s.id_starargs   = lambda *args: args
        s.id_kwargs     = lambda a=None,b=None: (a,b)
        s.id_starkwargs = lambda **kwargs: kwargs
        s.st_bare       = symboltable.SymbolTable(map={'a':'alpha', 'b':'beta', 'c':'gamma', 'd':'delta'})
        s.st_s         = symboltable.SymbolTable(map=dict(('s_'+k,v) for k,v in s.st_bare.iteritems()))
        s.st_vals         = s.st_bare.values()
        s.wifs = symboltable.wrap_input_for_symtable
        s.wofs = symboltable.wrap_output_for_symtable

    def test_mapping(s):
        pf_scalar, ins = s.wifs(s.id_scalar, {'a':'s_a'})
        s.assertEquals(pf_scalar(s.st_s), 'alpha')
        s.assertIn('s_a', ins)
        s.assertEquals(1, len(ins))
        pf_none, ins = s.wifs(s.id_none, {})
        s.assertIsNone(pf_none(s.st_s))
        s.assertEquals(0, len(ins))

        pf_pos, ins = s.wifs(s.id_pos, {'c':'s_c','b':'s_b','a':'s_a'})
        s.assertEquals(pf_pos(s.st_s), ('alpha', 'beta', 'gamma'))
        for k in ('s_a', 's_b', 's_c'):
            s.assertIn(k, ins)
        s.assertEquals(3, len(ins))
        # TODO: test all other functions.
    
