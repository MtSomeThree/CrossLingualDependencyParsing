__author__ = 'max'

import re
import numpy as np
import gurobipy as grb

def is_uni_punctuation(word):
    match = re.match("^[^\w\s]+$]", word, flags=re.UNICODE)
    return match is not None


def is_punctuation(word, pos, punct_set=None):
    if punct_set is None:
        return is_uni_punctuation(word)
    else:
        return pos in punct_set


def eval(words, postags, heads_pred, types_pred, heads, types, word_alphabet, pos_alphabet, lengths,
         punct_set=None, symbolic_root=False, symbolic_end=False, constraints_mask=None):
    batch_size, _ = words.shape
    ucorr = 0.
    lcorr = 0.
    total = 0.
    ucomplete_match = 0.
    lcomplete_match = 0.

    ucorr_nopunc = 0.
    lcorr_nopunc = 0.
    total_nopunc = 0.
    ucomplete_match_nopunc = 0.
    lcomplete_match_nopunc = 0.

    corr_root = 0.
    total_root = 0.
    start = 1 if symbolic_root else 0
    end = 1 if symbolic_end else 0
    for i in range(batch_size):
        ucm = 1.
        lcm = 1.
        ucm_nopunc = 1.
        lcm_nopunc = 1.
        for j in range(start, lengths[i] - end):
            flag = False
            if constraints_mask is not None:
                for constraint in constraints_mask:
                    res = constraint.pair_count(postags[i, j], postags[i, heads[i, j]])
                    if res != 0:
                        flag = True
                        break
                if not flag:
                    continue
           
            word = word_alphabet.get_instance(words[i, j])
            word = word.encode('utf8')

            pos = pos_alphabet.get_instance(postags[i, j])
            pos = pos.encode('utf8')

            total += 1
            if heads[i, j] == heads_pred[i, j]:
                ucorr += 1
                if types[i, j] == types_pred[i, j]:
                    lcorr += 1
                else:
                    lcm = 0
            else:
                ucm = 0
                lcm = 0

            if not is_punctuation(word, pos, punct_set):
                total_nopunc += 1
                if heads[i, j] == heads_pred[i, j]:
                    ucorr_nopunc += 1
                    if types[i, j] == types_pred[i, j]:
                        lcorr_nopunc += 1
                    else:
                        lcm_nopunc = 0
                else:
                    ucm_nopunc = 0
                    lcm_nopunc = 0

            if heads[i, j] == 0:
                total_root += 1
                corr_root += 1 if heads_pred[i, j] == 0 else 0

        ucomplete_match += ucm
        lcomplete_match += lcm
        ucomplete_match_nopunc += ucm_nopunc
        lcomplete_match_nopunc += lcm_nopunc

    return (ucorr, lcorr, total, ucomplete_match, lcomplete_match), \
           (ucorr_nopunc, lcorr_nopunc, total_nopunc, ucomplete_match_nopunc, lcomplete_match_nopunc), \
           (corr_root, total_root), batch_size


def decode_MST(energies, lengths, leading_symbolic=0, labeled=True):
    """
    decode best parsing tree with MST algorithm.
    :param energies: energies: numpy 4D tensor
        energies of each edge. the shape is [batch_size, num_labels, n_steps, n_steps],
        where the summy root is at index 0.
    :param masks: numpy 2D tensor
        masks in the shape [batch_size, n_steps].
    :param leading_symbolic: int
        number of symbolic dependency types leading in type alphabets)
    :return:
    """

    def find_cycle(par):
        added = np.zeros([length], np.bool)
        added[0] = True
        cycle = set()
        findcycle = False
        for i in range(1, length):
            if findcycle:
                break

            if added[i] or not curr_nodes[i]:
                continue

            # init cycle
            tmp_cycle = set()
            tmp_cycle.add(i)
            added[i] = True
            findcycle = True
            l = i

            while par[l] not in tmp_cycle:
                l = par[l]
                if added[l]:
                    findcycle = False
                    break
                added[l] = True
                tmp_cycle.add(l)

            if findcycle:
                lorg = l
                cycle.add(lorg)
                l = par[lorg]
                while l != lorg:
                    cycle.add(l)
                    l = par[l]
                break

        return findcycle, cycle

    def chuLiuEdmonds():
        par = np.zeros([length], dtype=np.int32)
        # create best graph
        par[0] = -1
        for i in range(1, length):
            # only interested at current nodes
            if curr_nodes[i]:
                max_score = score_matrix[0, i]
                par[i] = 0
                for j in range(1, length):
                    if j == i or not curr_nodes[j]:
                        continue

                    new_score = score_matrix[j, i]
                    if new_score > max_score:
                        max_score = new_score
                        par[i] = j

        # find a cycle
        findcycle, cycle = find_cycle(par)
        # no cycles, get all edges and return them.
        if not findcycle:
            final_edges[0] = -1
            for i in range(1, length):
                if not curr_nodes[i]:
                    continue

                pr = oldI[par[i], i]
                ch = oldO[par[i], i]
                final_edges[ch] = pr
            return

        cyc_len = len(cycle)
        cyc_weight = 0.0
        cyc_nodes = np.zeros([cyc_len], dtype=np.int32)
        id = 0
        for cyc_node in cycle:
            cyc_nodes[id] = cyc_node
            id += 1
            cyc_weight += score_matrix[par[cyc_node], cyc_node]

        rep = cyc_nodes[0]
        for i in range(length):
            if not curr_nodes[i] or i in cycle:
                continue

            max1 = float("-inf")
            wh1 = -1
            max2 = float("-inf")
            wh2 = -1

            for j in range(cyc_len):
                j1 = cyc_nodes[j]
                if score_matrix[j1, i] > max1:
                    max1 = score_matrix[j1, i]
                    wh1 = j1

                scr = cyc_weight + score_matrix[i, j1] - score_matrix[par[j1], j1]

                if scr > max2:
                    max2 = scr
                    wh2 = j1

            score_matrix[rep, i] = max1
            oldI[rep, i] = oldI[wh1, i]
            oldO[rep, i] = oldO[wh1, i]
            score_matrix[i, rep] = max2
            oldO[i, rep] = oldO[i, wh2]
            oldI[i, rep] = oldI[i, wh2]

        rep_cons = []
        for i in range(cyc_len):
            rep_cons.append(set())
            cyc_node = cyc_nodes[i]
            for cc in reps[cyc_node]:
                rep_cons[i].add(cc)

        for i in range(1, cyc_len):
            cyc_node = cyc_nodes[i]
            curr_nodes[cyc_node] = False
            for cc in reps[cyc_node]:
                reps[rep].add(cc)

        chuLiuEdmonds()

        # check each node in cycle, if one of its representatives is a key in the final_edges, it is the one.
        found = False
        wh = -1
        for i in range(cyc_len):
            for repc in rep_cons[i]:
                if repc in final_edges:
                    wh = cyc_nodes[i]
                    found = True
                    break
            if found:
                break

        l = par[wh]
        while l != wh:
            ch = oldO[par[l], l]
            pr = oldI[par[l], l]
            final_edges[ch] = pr
            l = par[l]

    if labeled:
        assert energies.ndim == 4, 'dimension of energies is not equal to 4'
    else:
        assert energies.ndim == 3, 'dimension of energies is not equal to 3'
    input_shape = energies.shape
    batch_size = input_shape[0]
    max_length = input_shape[2]

    pars = np.zeros([batch_size, max_length], dtype=np.int32)
    types = np.zeros([batch_size, max_length], dtype=np.int32) if labeled else None
    for i in range(batch_size):
        energy = energies[i]

        # calc the realy length of this instance
        length = lengths[i]

        # calc real energy matrix shape = [length, length, num_labels - #symbolic] (remove the label for symbolic types).
        if labeled:
            energy = energy[leading_symbolic:, :length, :length]
            # get best label for each edge.
            label_id_matrix = energy.argmax(axis=0) + leading_symbolic
            energy = energy.max(axis=0)
        else:
            energy = energy[:length, :length]
            label_id_matrix = None
        # get original score matrix
        orig_score_matrix = energy
        # initialize score matrix to original score matrix
        score_matrix = np.array(orig_score_matrix, copy=True)

        oldI = np.zeros([length, length], dtype=np.int32)
        oldO = np.zeros([length, length], dtype=np.int32)
        curr_nodes = np.zeros([length], dtype=np.bool)
        reps = []

        for s in range(length):
            orig_score_matrix[s, s] = 0.0
            score_matrix[s, s] = 0.0
            curr_nodes[s] = True
            reps.append(set())
            reps[s].add(s)
            for t in range(s + 1, length):
                oldI[s, t] = s
                oldO[s, t] = t

                oldI[t, s] = t
                oldO[t, s] = s

        final_edges = dict()
        chuLiuEdmonds()
        par = np.zeros([max_length], np.int32)
        if labeled:
            type = np.ones([max_length], np.int32)
            type[0] = 0
        else:
            type = None

        for ch, pr in final_edges.items():
            par[ch] = pr
            if labeled and ch != 0:
                type[ch] = label_id_matrix[pr, ch]

        par[0] = 0
        pars[i] = par
        if labeled:
            types[i] = type

    return pars, types

def decode_proj(energies, lengths, leading_symbolic=0, labeled=True):

    def Projective_MST(N, dist, arc):
        f = np.zeros((N + 1, N))    # max score that connect [i, j] to i - 1 or j + 1
        g = np.zeros((N + 1, N))    # max scroe that connect [i, j] to i - 1

        traceBackF = np.zeros((N + 1, N), dtype='int32')    # divide point for f[i, j], -1 for g[i, j]
        traceBackG = np.zeros((N + 1, N), dtype='int32')    # divide point for g[i, j]
        for width in range(N - 1):
            for i in range(1, N - width):
                j = i + width

                temp_max = [-2e+8, -1]
                for k in range(i, j + 1):
                    if (i - 1, k) not in arc:
                        continue
                    score = f[i, k - 1] + g[k + 1, j] + dist[i - 1, k]
                    if not isinstance(score, float):
                        print(f[i, k - 1], g[k + 1, j], dist[i - 1, k])
                        print (i, j, k)
                        print (dist.shape)
                    if score > temp_max[0]:
                        temp_max = [score, k]
                g[i, j], traceBackG[i, j] = temp_max

                if width == N - 1:
                    continue
                temp_max = [g[i, j], -1]
                for k in range(i, j + 1):
                    if (j + 1, k) not in arc:
                        continue
                    score = f[i, k - 1] + f[k + 1, j] + dist[j + 1, k]
                    if score > temp_max[0]:
                        temp_max = [score, k]
                f[i, j], traceBackF[i, j] = temp_max
        edgeSet = set()
        def TraceBackEdgeF(left, right):
            if left > right:
                return
            if traceBackF[left, right] == -1:
                TraceBackEdgeG(left, right)
            else:
                k = traceBackF[left, right]
                edgeSet.add((right + 1, k))
                TraceBackEdgeF(left, k - 1)
                TraceBackEdgeF(k + 1, right)

        def TraceBackEdgeG(left, right):
            if left > right:
                return
            k = traceBackG[left, right]
            edgeSet.add((left - 1, k))
            TraceBackEdgeF(left, k - 1)
            TraceBackEdgeG(k + 1, right)

        TraceBackEdgeG(1, N - 1)
        solution = np.zeros((N, N))

        return g[1, N - 1], edgeSet

    input_shape = energies.shape
    batch_size = input_shape[0]
    max_length = input_shape[2]

    pars = np.zeros([batch_size, max_length], dtype=np.int32)
    types = np.zeros([batch_size, max_length], dtype=np.int32) if labeled else None
    for batch_id in range(batch_size):
        energy = energies[batch_id]
        # calc the realy length of this instance
        length = lengths[batch_id]

        # calc real energy matrix shape = [length, length, num_labels - #symbolic] (remove the label for symbolic types).
        if labeled:
            energy = energy[leading_symbolic:, :length, :length]
            # get best label for each edge.
            label_id_matrix = energy.argmax(axis=0) + leading_symbolic
            energy = energy.max(axis=0)
        else:
            energy = energy[:length, :length]
            label_id_matrix = None
        # get original score matrix
        orig_score_matrix = energy
        # initialize score matrix to original score matrix
        score_matrix = np.array(orig_score_matrix, copy=True)
        arc = set()
        for i in range(length):
            for j in range(i + 1, length):
                arc.add((i, j))
                arc.add((j, i))
        ans, edges = Projective_MST(length, score_matrix, arc)
        par = np.zeros([max_length], np.int32)
        if labeled:
            type = np.ones([max_length], np.int32)
            type[0] = 0
        else:
            type = None
        for (i, j) in edges:
            par[j] = i
            if labeled:
                type[j] = label_id_matrix[i, j]
        par[0] = 0
        pars[batch_id] = par
        if labeled:
            types[batch_id] = type

    return pars, types

def decode_ILP(energies, lengths, leading_symbolic=0, labeled=True):
    """
    decode best parsing tree with MST algorithm.
    :param energies: energies: numpy 4D tensor
        energies of each edge. the shape is [batch_size, num_labels, n_steps, n_steps],
        where the summy root is at index 0.
    :param masks: numpy 2D tensor
        masks in the shape [batch_size, n_steps].
    :param leading_symbolic: int
        number of symbolic dependency types leading in type alphabets)
    :return:
    """
    return decode_proj(energies, lengths, leading_symbolic, labeled)
    '''
    def GRBModel_MST(N, dist, arc, projective=False):

        m = grb.Model('mst')

        z = m.addVars(arc, vtype=grb.GRB.BINARY, name='z')
        flow = m.addVars(arc, vtype=grb.GRB.CONTINUOUS, name='flow')
        
        m.addConstrs((flow[i, j] >= 0 for i, j in arc), "non-negative_flow")

        for i in range(N):
            if i == 0:
                m.addConstr(z.sum('*', i) == 0, "outgoing%d"%(i))
            else:
                m.addConstr(z.sum('*', i) == 1, "outgoing%d"%(i))

        m.addConstr(flow.sum(0, '*') == N - 1, "flow%d"%(0))
        for i in range(1, N):
            m.addConstr(flow.sum('*', i) - flow.sum(i, '*') == 1, "flow%d"%(i))

        m.addConstrs((flow[i, j] <= (N - 1) * z[i, j] for i, j in arc), "feasiable_flow")


        if projective:
            for (i, j) in arc:
                M = 0
                left = min(i, j)
                right = max(i, j)
                conflict_arc = set()
                for k in range(left + 1, right):
                    for l in range(left):
                        if (k, l) in arc:
                            conflict_arc.add((k, l))
                            M += 1
                        if (l, k) in arc:
                            conflict_arc.add((l, k))
                            M += 1
                        #M += 2
                    for l in range(right + 1, N):
                        if (k, l) in arc:
                            conflict_arc.add((k, l))
                            M += 1
                        if (l, k) in arc:
                            conflict_arc.add((l, k))
                            M += 1
                        #M += 2
                expr = sum(z[k, l] for k, l in conflict_arc)
                m.addConstr(M * z[i, j] + expr <= M, "projective (%d, %d)"%(i, j))
                

        m.setObjective(sum(z[i, j] * dist[i, j] for i, j in arc), grb.GRB.MAXIMIZE)

        m.setParam("LogToConsole", 0)
        return m

    input_shape = energies.shape
    batch_size = input_shape[0]
    max_length = input_shape[2]

    pars = np.zeros([batch_size, max_length], dtype=np.int32)
    types = np.zeros([batch_size, max_length], dtype=np.int32) if labeled else None
    for batch_id in range(batch_size):
        energy = energies[batch_id]

        # calc the realy length of this instance
        length = lengths[batch_id]

        # calc real energy matrix shape = [length, length, num_labels - #symbolic] (remove the label for symbolic types).
        if labeled:
            energy = energy[leading_symbolic:, :length, :length]
            # get best label for each edge.
            label_id_matrix = energy.argmax(axis=0) + leading_symbolic
            energy = energy.max(axis=0)
        else:
            energy = energy[:length, :length]
            label_id_matrix = None
        # get original score matrix
        orig_score_matrix = energy
        # initialize score matrix to original score matrix
        score_matrix = np.array(orig_score_matrix, copy=True)
        arc = set()
        for i in range(length):
            for j in range(i + 1, length):
                arc.add((i, j))
                arc.add((j, i))
        if length < 20:
            model = GRBModel_MST(length, score_matrix, arc, projective=True)
        else:
            model = GRBModel_MST(length, score_matrix, arc, projective=False)
        model.optimize()

        par = np.zeros([max_length], np.int32)
        if labeled:
            type = np.ones([max_length], np.int32)
            type[0] = 0
        else:
            type = None
        for v in model.getVars():
            if v.varName[0] == 'z':
                index = [int(xx) for xx in v.varName[2:-1].split(',')]
                if int(v.x + 1e-6) == 1:
                    par[index[1]] = index[0]
                    if labeled:
                        type[index[1]] = label_id_matrix[index[0], index[1]]
        par[0] = 0
        pars[batch_id] = par
        if labeled:
            types[batch_id] = type

    return pars, types
    '''
