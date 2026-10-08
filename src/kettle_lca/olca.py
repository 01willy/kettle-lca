"""Matrix-based LCA on an openLCA JSON-LD package.

Builds the technosphere matrix A and the intervention matrices from the
exchanges in the package, links inputs to providers, and solves
A s = f; g = B s; h = c g  (Suh and Heijungs, 2007).

Each column of A is a provider flow: a (process, product) pair. A
multi-output process is split into one column per product output using
the process's default allocation method (physical, economic or causal
factors stored in the package). Sign conventions follow openLCA: product
outputs and waste-treatment references are positive, linked product
inputs and waste outputs are negative. Elementary exchanges are stored as
positive amounts in separate output and input matrices; a
characterization factor applies to the net amount in the direction of the
flow's context (resource = input).
"""

import json
import zipfile
from collections import defaultdict

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

FOLDERS = ("processes", "flows", "unit_groups", "flow_properties",
           "lcia_categories", "lcia_methods")


class Package:
    """In-memory view of an openLCA JSON-LD zip."""

    def __init__(self, path):
        self.path = path
        self.data = {key: {} for key in FOLDERS}
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.endswith("/") or "/" not in name:
                    continue
                folder = name.split("/")[0]
                if folder in self.data:
                    obj = json.loads(z.read(name))
                    self.data[folder][obj["@id"]] = obj
        self.processes = self.data["processes"]
        self.flows = self.data["flows"]
        self.unit_factor = {}
        for group in self.data["unit_groups"].values():
            for unit in group.get("units", []):
                self.unit_factor[unit["@id"]] = unit.get("conversionFactor", 1.0)
        self.fp_factor = {}
        self.ref_fp = {}
        for flow in self.flows.values():
            for fpf in flow.get("flowProperties", []):
                fp_id = fpf["flowProperty"]["@id"]
                self.fp_factor[(flow["@id"], fp_id)] = fpf.get("conversionFactor", 1.0)
                if fpf.get("isRefFlowProperty"):
                    self.ref_fp[flow["@id"]] = fp_id

    def ref_amount(self, exchange):
        """Exchange amount in the reference unit of its flow."""
        amount = exchange.get("amount", 0.0) or 0.0
        unit = exchange.get("unit") or {}
        factor = self.unit_factor.get(unit.get("@id"), 1.0)
        flow_id = exchange["flow"]["@id"]
        fp = (exchange.get("flowProperty") or {}).get("@id", self.ref_fp.get(flow_id))
        fp_factor = self.fp_factor.get((flow_id, fp), 1.0) or 1.0
        return amount * factor / fp_factor

    def find(self, name_startswith):
        hits = [p for p in self.processes.values() if p.get("name", "").startswith(name_startswith)]
        if len(hits) != 1:
            raise KeyError(f"{len(hits)} processes match {name_startswith!r}")
        return hits[0]


def ref_exchange(process):
    for e in process.get("exchanges", []):
        if e.get("isQuantitativeReference"):
            return e
    return None


def product_outputs(process):
    return [e for e in process.get("exchanges", [])
            if e["flow"].get("flowType") == "PRODUCT_FLOW" and not e.get("isInput")
            and not e.get("isAvoidedProduct")]


class System:
    """Linked technosphere and intervention matrices for all processes."""

    def __init__(self, pkg):
        self.pkg = pkg
        self.techflows = []          # (process id, product flow id)
        self.index = {}
        self.alloc_notes = []
        columns = []                 # (process, product exchange, product exchanges)
        for p in pkg.processes.values():
            ref = ref_exchange(p)
            if ref is None:
                continue
            products = product_outputs(p)
            is_treatment = ref["flow"].get("flowType") == "WASTE_FLOW" and ref.get("isInput")
            heads = [ref] if (is_treatment or len(products) <= 1) else products
            for head in heads:
                key = (p["@id"], head["flow"]["@id"])
                if key in self.index:
                    continue
                self.index[key] = len(self.techflows)
                self.techflows.append(key)
                columns.append((p, head, heads if len(heads) > 1 else [head]))
        self.producers = defaultdict(list)
        for key in self.techflows:
            self.producers[key[1]].append(key)

        n = len(self.techflows)
        a_r, a_c, a_v = [], [], []
        out_e, in_e = defaultdict(float), defaultdict(float)
        self.elem_ids, self.elem_index = [], {}
        self.unresolved = []
        for j, (p, head, heads) in enumerate(columns):
            a_r.append(j); a_c.append(j); a_v.append(pkg.ref_amount(head))
            head_ids = {id(h) for h in heads}
            for e in p["exchanges"]:
                if id(e) in head_ids or e is head:
                    continue
                amount = pkg.ref_amount(e)
                if amount == 0:
                    continue
                if len(heads) > 1:
                    amount *= self._alloc(p, head, e)
                    if amount == 0:
                        continue
                ftype = e["flow"].get("flowType")
                if ftype == "ELEMENTARY_FLOW":
                    fid = e["flow"]["@id"]
                    if fid not in self.elem_index:
                        self.elem_index[fid] = len(self.elem_ids)
                        self.elem_ids.append(fid)
                    target = in_e if e.get("isInput") else out_e
                    target[(self.elem_index[fid], j)] += amount
                    continue
                is_input = bool(e.get("isInput"))
                avoided = bool(e.get("isAvoidedProduct"))
                if ftype == "PRODUCT_FLOW" and not is_input and not avoided:
                    continue  # co-product of a process without allocation factors
                if ftype == "WASTE_FLOW" and is_input:
                    self.unresolved.append((j, e["flow"]["@id"], e["flow"].get("name"), amount, "waste input"))
                    continue
                provider = self._provider(e)
                if provider is None:
                    self.unresolved.append((j, e["flow"]["@id"], e["flow"].get("name"), amount, "no provider"))
                    continue
                a_r.append(provider); a_c.append(j); a_v.append((1.0 if avoided else -1.0) * amount)
        self.A = sp.csc_matrix((a_v, (a_r, a_c)), shape=(n, n))
        m = len(self.elem_ids)
        self.B_out = self._sparse(out_e, m, n)
        self.B_in = self._sparse(in_e, m, n)
        u_keys, u_r, u_c, u_v = {}, [], [], []
        for j, fid, name, amount, reason in self.unresolved:
            key = (fid, name, reason)
            u_keys.setdefault(key, len(u_keys))
            u_r.append(u_keys[key]); u_c.append(j); u_v.append(amount)
        self.unresolved_keys = list(u_keys)
        self.U = sp.csc_matrix((u_v, (u_r, u_c)), shape=(max(len(u_keys), 1), n))
        self._lu = spla.splu(self.A)

    def _alloc(self, process, head, exchange):
        """Allocation factor of `exchange` to product `head`."""
        method = process.get("defaultAllocationMethod") or "NO_ALLOCATION"
        factors = process.get("allocationFactors") or []
        product = head["flow"]["@id"]
        if method == "NO_ALLOCATION" or not factors:
            if head.get("isQuantitativeReference"):
                return 1.0
            self.alloc_notes.append((process["name"], "no factors; burden kept on reference product"))
            return 0.0
        if method == "CAUSAL_ALLOCATION":
            internal_id = exchange.get("internalId")
            for af in factors:
                if (af.get("allocationType") == "CAUSAL_ALLOCATION"
                        and af.get("product", {}).get("@id") == product
                        and (af.get("exchange") or {}).get("internalId") == internal_id):
                    return af.get("value", 0.0)
            method = "PHYSICAL_ALLOCATION"
        for af in factors:
            if af.get("allocationType") == method and af.get("product", {}).get("@id") == product:
                return af.get("value", 0.0)
        return 0.0

    @staticmethod
    def _sparse(entries, m, n):
        if not entries:
            return sp.csc_matrix((m, n))
        keys = list(entries)
        return sp.csc_matrix(([entries[k] for k in keys],
                              ([k[0] for k in keys], [k[1] for k in keys])), shape=(m, n))

    def _provider(self, exchange):
        flow = exchange["flow"]["@id"]
        prov = (exchange.get("defaultProvider") or {}).get("@id")
        if prov is not None and (prov, flow) in self.index:
            return self.index[(prov, flow)]
        candidates = self.producers.get(flow, [])
        if len(candidates) == 1:
            return self.index[candidates[0]]
        return None

    def column(self, process):
        """Column index of a process's reference product."""
        return self.index[(process["@id"], ref_exchange(process)["flow"]["@id"])]

    def solve(self, demand):
        """demand: {column index: amount in the reference unit of the product}."""
        f = np.zeros(len(self.techflows))
        for j, amount in demand.items():
            f[j] += amount
        return self._lu.solve(f)

    def cf_vectors(self, category):
        """Characterization factors aligned with the elementary-flow index.

        Returns (c_out, c_in), applied to output and input amounts.
        """
        c_out = np.zeros(len(self.elem_ids))
        c_in = np.zeros(len(self.elem_ids))
        for factor in category.get("impactFactors", []):
            fid = factor["flow"]["@id"]
            if fid not in self.elem_index:
                continue
            unit = (factor.get("unit") or {}).get("@id")
            fp = (factor.get("flowProperty") or {}).get("@id", self.pkg.ref_fp.get(fid))
            k = self.pkg.unit_factor.get(unit, 1.0) / (self.pkg.fp_factor.get((fid, fp), 1.0) or 1.0)
            value = factor["value"] / k
            i = self.elem_index[fid]
            if "/resource" in (factor["flow"].get("category") or ""):
                c_in[i], c_out[i] = value, -value
            else:
                c_out[i], c_in[i] = value, -value
        return c_out, c_in

    def impacts_by_column(self, s, c_out, c_in):
        """Direct characterized result of each column scaled by s."""
        per_unit = self.B_out.T @ c_out + self.B_in.T @ c_in
        return per_unit * s
