from pdb import set_trace
import sys, os
sys.path.append(os.getcwd() + "/..")

import numpy as np
import autompc as ampc
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from joblib import Memory

from scipy.integrate import solve_ivp

memory = Memory("cache")

cartpole = ampc.System(["theta", "omega", "x", "dx"], ["u"])

def cartpole_dynamics(y, u, g = 1.0, m_c = 1, m_p = 1, L = 1, b = 1.0):
    """
    Parameters
    ----------
        y : states
        u : control

    Returns
    -------
        A list describing the dynamics of the cart cart pole
    """
    theta, omega, x, dx = y
    #return [omega,
    #        g * np.sin(theta)/L - b * omega / (m*L**2) + u * np.sin(theta)/L,
    #        dx,
    #        u]
    return [omega,
            1.0/(L*(m_c+m_p+m_p*np.sin(theta)**2))*(-u*np.cos(theta) 
                - m_p*L*omega**2*np.cos(theta)*np.sin(theta)
                - (m_c+m_p+m_p)*g*np.sin(theta)
                - b*omega),
            dx,
            1.0/(m_c + m_p*np.sin(theta)**2)*(u + m_p*np.sin(theta)*
                (L*omega**2 + g*np.cos(theta)))]

def dt_cartpole_dynamics(y,u,dt,g=9.8,m=1,L=1,b=1.0):
    y[0] += np.pi
    sol = solve_ivp(lambda t, y: cartpole_dynamics(y, u, g, m, L, b), (0, dt), y, t_eval = [dt])
    if not sol.success:
        raise Exception("Integration failed due to {}".format(sol.message))
    y = sol.y.reshape((4,))
    y[0] %= 2 * np.pi
    y[0] -= np.pi
    return sol.y.reshape((4,))

def animate_cartpole(fig, ax, dt, traj):
    ax.grid()

    line, = ax.plot([0.0, 0.0], [0.0, -1.0], 'o-', lw=2)
    time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes)
    ctrl_text = ax.text(0.7, 0.95, '', transform=ax.transAxes)

    def init():
        line.set_data([0.0, 0.0], [0.0, -1.0])
        time_text.set_text('')
        return line, time_text

    def animate(i):
        #i = min(i, ts.shape[0])
        line.set_data([traj[i,"x"], traj[i,"x"]+np.sin(traj[i,"theta"]+np.pi)], 
                [0, -np.cos(traj[i,"theta"] + np.pi)])
        time_text.set_text('t={:.2f}'.format(dt*i))
        ctrl_text.set_text("u={:.2f}".format(traj[i,"u"]))
        return line, time_text

    ani = animation.FuncAnimation(fig, animate, frames=traj.size, interval=dt*1000,
            blit=False, init_func=init, repeat_delay=1000)

    return ani

dt = 0.01

umin = -2.0
umax = 2.0
udmax = 0.25

# Generate trajectories for training
num_trajs = 100

@memory.cache
def gen_trajs():
    rng = np.random.default_rng(49)
    trajs = []
    for _ in range(num_trajs):
        theta0 = rng.uniform(-0.02, 0.02, 1)[0]
        y = [theta0, 0.0, 0.0, 0.0]
        traj = ampc.zeros(cartpole, 400)
        for i in range(400):
            traj[i].obs[:] = y
            #if u[0] > umax:
            #    u[0] = umax
            #if u[0] < umin:
            #    u[0] = umin
            #u += rng.uniform(-udmax, udmax, 1)
            u  = rng.uniform(umin, umax, 1)
            y = dt_cartpole_dynamics(y, u, dt)
            traj[i].ctrl[:] = u
        trajs.append(traj)
    return trajs
trajs = gen_trajs()

from autompc.sysid import ARX, Koopman#, SINDy

@memory.cache
def train_arx(k=2):
    cs = ARX.get_configuration_space(cartpole)
    cfg = cs.get_default_configuration()
    cfg["history"] = k
    arx = ampc.make_model(cartpole, ARX, cfg)
    arx.train(trajs)
    return arx

#@memory.cache
def train_koop():
    cs = Koopman.get_configuration_space(cartpole)
    cfg = cs.get_default_configuration()
    cfg["trig_basis"] = "true"
    cfg["poly_basis"] = "false"
    cfg["method"] = "lstsq"
    koop = ampc.make_model(cartpole, Koopman, cfg)
    koop.train(trajs)
    return koop

def train_sindy():
    sindy = SINDy(cartpole)
    sindy.train(trajs)
    return sindy

arx = train_arx(k=4)
koop = train_koop()
#sindy = train_sindy()
#set_trace()

# Test prediction

#traj = trajs[0]
#predobs, _ = koop.pred(traj[:10])

#koop_A, koop_B, state_func, cost_func = koop.to_linear()

#state = state_func(traj[:10])
#
#state = koop_A @ state + koop_B @ traj[10].ctrl
#state = koop_A @ state + koop_B @ traj[11].ctrl

#assert(np.allclose(state[-3:-1], traj[11].obs))

model = koop
Model = Koopman

if True:
    from autompc.evaluators import HoldoutEvaluator
    from autompc.metrics import RmseKstepMetric
    from autompc.graphs import KstepGrapher, InteractiveEvalGrapher

    metric = RmseKstepMetric(cartpole, k=50)
    #grapher = KstepGrapher(pendulum, kmax=50, kstep=5, evalstep=10)
    grapher = InteractiveEvalGrapher(cartpole)

    rng = np.random.default_rng(42)
    evaluator = HoldoutEvaluator(cartpole, trajs, metric, rng, holdout_prop=0.25) 
    evaluator.add_grapher(grapher)
    cs = Model.get_configuration_space(cartpole)
    cfg = cs.get_default_configuration()
    cfg["trig_basis"] = "true"
    cfg["method"] = "lstsq"
    #cfg["poly_basis"] = "true"
    #cfg["poly_degree"] = 3
    #cfg["history"] = 4
    eval_score, _, graphs = evaluator(Model, cfg)
    print("eval_score = {}".format(eval_score))
    fig = plt.figure()
    graph = graphs[0]
    graph.set_obs_lower_bound("theta", -0.2)
    graph.set_obs_upper_bound("theta", 0.2)
    graph.set_obs_lower_bound("omega", -0.2)
    graph.set_obs_upper_bound("omega", 0.2)
    #graph.set_obs_lower_bound("dx", -0.2)
    #graph.set_obs_upper_bound("dx", 0.2)
    #graph.set_obs_lower_bound("x", -0.2)
    #graph.set_obs_upper_bound("x", 0.2)
    graphs[0](fig)
    #plt.tight_layout()
    plt.show()


from autompc.control import FiniteHorizonLQR
#from autompc.control.mpc import LQRCost, LinearMPC

task = ampc.Task(cartpole)
Q = np.diag([1.0, 10.0, 10.0, 10.0])
R = np.diag([0.001])
task.set_quad_cost(Q, R)


cs = FiniteHorizonLQR.get_configuration_space(cartpole, task, model)
cfg = cs.get_default_configuration()
cfg["horizon"] = 200
con = ampc.make_controller(cartpole, task, model, FiniteHorizonLQR, cfg)

sim_traj = ampc.zeros(cartpole, 1)
x = np.array([0.0,0.05,0.0,0.0])
sim_traj[0].obs[:] = x

constate = con.traj_to_state(sim_traj[:1])
for _ in range(1000):
    u, constate = con.run(constate, sim_traj[-1].obs)
    x = dt_cartpole_dynamics(x, u, dt)
    sim_traj[-1, "u"] = u
    sim_traj = ampc.extend(sim_traj, [x], [[0.0]])

#plt.plot(sim_traj[:,"x1"], sim_traj[:,"x2"], "b-o")
#plt.show()
print("K:")
print(con.K)

fig = plt.figure()
ax = fig.gca()
ax.set_aspect("equal")
ax.set_xlim([-1.1, 1.1])
ax.set_ylim([-1.1, 1.1])
#set_trace()
ani = animate_cartpole(fig, ax, dt, sim_traj)
#ani.save("out/test4/cartpole.mp4")
plt.show()
