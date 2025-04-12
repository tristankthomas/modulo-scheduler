from src.utilities.ilp_manager import *
from src.utilities.cdfg_manager import *
import logging
from collections import defaultdict

############################################################################################################################################
############################################################################################################################################
#
#	`RESOURCE_MANAGER` CLASS
#
############################################################################################################################################
#	DESCRIPTION:
#					The following class is used for resource sharing in CDFG (Control DataFlow Graph) representing a function.
############################################################################################################################################
#	ATTRIBUTES:
#					- ilp : ILP problem of the class ILP
#					- constraint_set : set of constraints of the class CONSTRAINT_SET
#					- obj_function : optimization function of the class Obj_Function
#					- log: logger object used to output logs
############################################################################################################################################
#	FUNCTIONS:
# 					- add_resource_constraints : setting up the maximum resource usage per res type in the constraint set
#					- add_resource_constraints_pipelined : add resources constraints for pipelined scheduling
#					- check_resource_dict : validate values in resource dict
############################################################################################################################################
############################################################################################################################################

allowed_resources = ["load", "add", "mul", "div", "zext"]

class Resource_Manager:
	def __init__(self, parser, ilp_dependency_inj, log=None, ):
		assert(parser != None) # ensure Parser is different from None
		assert(ilp_dependency_inj != None) # ensure ilp source is different from None
		self.cdfg = parser.get_cdfg() # save the CDFG of the parser
		self.cfg = parser.get_cfg() # save the CFG of the parser
		if log != None:
			self.log = log
		else:
			self.log = logging.getLogger('resource') # if the logger is not given at object generation, create a new one
		
		ilp_dependency_inj(self)

	"""
	Adds scheduling ILP created by the Scheduler must be passed to the Resources
	"""
	def set_scheduling_ilp(self, ilp, constraints, obj_fun):
		self.ilp = ilp
		self.constraints = constraints
		self.obj_fun = obj_fun


	"""
	Adds constraints to the constraint set that enforce the resource constraints contained in the resource dictionary
	"""
	def add_resource_constraints(self, resource_dict):
		inequality_sign = "geq"
		self.check_resource_dict(resource_dict)

		sorted_nodes = get_topological_order(self.cdfg)
		bbs_dict = defaultdict(list)
		for node in sorted_nodes:
			bbs_dict[node.attr["id"]].append(node)
		bbs = list(bbs_dict.values())

		for res in resource_dict.keys():
			for bb in bbs:
				# extract just the restricted resource
				constraint = resource_dict[res]
				nodes = [node for node in bb if res == node.attr["type"]]
				nodes.sort(key=lambda node: "inc" not in node)
				for i, nodeA in enumerate(nodes):
					index = i + constraint
					if index < len(nodes):
						nodeB = nodes[index]
						lhs_dictionary = {f"sv{nodeA}": -1, f"sv{nodeB}": 1}
						rhs = 1
						self.constraints.add_constraint(lhs_dictionary, inequality_sign, rhs)

		

	# function to add resources constraints for pipelined scheduling
	def check_resource_constraints_pipelined(self, resource_dict, II):
		self.check_resource_dict(resource_dict)

		mrt = defaultdict(list)
		for node in self.cdfg:
			columnIndex = self.ilp.get_operation_timing_solution(node) % II
			mrt[columnIndex].append(node.attr["type"])

		for res, constraint in resource_dict.items():
			for ops in mrt.values():
				if ops.count(res) > constraint:
					return False

		return True

	"""
	Checks the types specified in the given resource dictionary(a dictionary containing something like "bogusoperationtype" wouldn't be valid) and sets the resource_dic member variable of the class to the specified resource dictionary
	@param resource_dic: the resource dictionary that the class should use
	"""
	def check_resource_dict(self, resource_dict):
		for resource in resource_dict:
			if not(resource in allowed_resources): # the resource type should be present in the list of allowed resource types
				self.log.error("Resource {0} is not allowed (allowed resources = {1})".format(resource, allowed_resources))
				continue