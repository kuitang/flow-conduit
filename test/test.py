import test_bootstrap
from flowconduit import ControlGraph
#from flowconduit import ControlGraph

cg = ControlGraph()
def start():
    return ('alpha', 'beta')
    
def a_plus_b(alpha, beta):
    return alpha + beta
    
def bb(beta):
    return {'a':beta, 'b':beta}
    

cg.add_func(start, outputs=['alpha', 'beta'])
    

cg.add_func(start, outputs=['alpha', 'beta'])
print cg.supplier
cg.supplier['alpha'].__dict__
cg.add_func(a_plus_b, inputs=['alpha', 'beta'], outputs='omega')
cg.add_func(bb, inputs=['beta'], outputs={'a':'sym_a', 'b':'sym_b'})
cg.finalize()

print cg.run('sym_a')
