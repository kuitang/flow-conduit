from flowconduit import ControlGraph
cg = ControlGraph()
def start():
    return ('alpha', 'beta')
    
def a_plus_b(alpha, beta):
    return alpha + beta
    
def bb(beta):
    return {'a':beta, 'b':beta}
    

cg.add_func(start, outputs=['alpha', 'beta'])
# OUT: Traceback (most recent call last):
# OUT:   File "<input>", line 1, in <module>
# OUT: NameError: name 'start' is not defined
start
# OUT: Traceback (most recent call last):
# OUT:   File "<input>", line 1, in <module>
# OUT: NameError: name 'start' is not defined
def start():
    return ('alpha', 'beta')
    

cg.add_func(start, outputs=['alpha', 'beta'])
cg.supplier
# OUT: {'alpha': <flowconduit.GraphFunc object at 0x1013fd3d0>, 'beta': <flowconduit.GraphFunc object at 0x1013fd3d0>}
cg.supplier['alpha'].__dict__
# OUT: {'output_syms': ['alpha', 'beta'], 'input_syms': None, 'prepared_f': <function <lambda> at 0x1013f2398>, 'name': 'start', 'output': <function osym_sequence at 0x1013f22a8>}
cg.add_func(a_plus_b, inputs=['alpha', 'beta'], outputs='omega')
cg.add_func(bb, inputs=['beta'], outputs={'a':'sym_a', 'b':'sym_b'})
cg.finalize()

print cg.run('sym_a')
