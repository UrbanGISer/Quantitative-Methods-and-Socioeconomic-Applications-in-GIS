def scal(c, x, s, n):
	# Scales a vector by a constant
	for i in range(n):
		j = s + i
		x[j] = c * x[j]

def axpy(c, x, y, sx, sy, n):
	# Constant times a vector plus a vector
	for i in range(n):
		jx = sx + i
		jy = sy + i
		y[jy] = y[jy] + c * x[jx]

def ludcomp(a, n, m, ipvt, err_info):
	# ludcomp computes the L-U factors of a square
	# matrix by Gaussian elimination with pivoting
	#
	# adapted from linpack

	err_info = 0
	for k in range(n-1):
		# Find pivot index
		ip = k
		dmax = abs(a[k][k])
		for i in range(k+1, n):
			dtmp = abs(a[k][i])
			if dtmp <= dmax:
				continue
			ip = i
			dmax = dtmp
		ipvt[k] = ip
		# Zero pivot implies column already triangularized
		if a[k][ip] == 0:
			err_info = k
			continue
		# Exchange if necessary
		if ip != k:
			t = a[k][ip]
			a[k][ip] = a[k][k]
			a[k][k] = t
		# Compute multipliers
		t = -1.0 / a[k][k]
		scal(t, a[k], k+1, n-k-1)
		# Row elimination with column indexing
		for j in range(k+1, n):
			t = a[j][ip]
			if ip != k:
				a[j][ip] = a[j][k]
				a[j][k] = t
			axpy(t, a[k], a[j], k+1, k+1, n-k-1)
	ipvt[n-1] = n-1
	if a[n-1][n-1] == 0:
		err_info = n-1

def lusolve(a, b, n, m, ipvt):
	# lusolve solves the double precision system
	# a * x = b using factors computed by ludcomp
	#
	# adapted from linpack

	# First solve l*y = b
	for k in range(n-1):
		l = ipvt[k]
		t = b[l]
		if l != k:
			b[l] = b[k]
			b[k] = t
		axpy(t, a[k], b, k+1, k+1, n-k-1)

	# Now solve u*x = y
	for k in range(n-1, -1, -1):
		b[k] = b[k] / a[k][k]
		t = -b[k]
		axpy(t, a[k], b, 0, 0, k)

# Import system modules
import arcpy, arcpy.da

# Get input parameters
locationFL = arcpy.GetParameterAsText(0)
locationIdField = arcpy.GetParameterAsText(1)
basicEmplField = arcpy.GetParameterAsText(2)
serviceEmplField = arcpy.GetParameterAsText(3)
popField = arcpy.GetParameterAsText(4)
distanceTable = arcpy.GetParameterAsText(5)
originIdField = arcpy.GetParameterAsText(6)
destIdField = arcpy.GetParameterAsText(7)
distanceField = arcpy.GetParameterAsText(8)
distanceDecayFunc = arcpy.GetParameterAsText(9)
strALPHA = arcpy.GetParameterAsText(10)
strBETA = arcpy.GetParameterAsText(11)
strH = arcpy.GetParameterAsText(12)
strE = arcpy.GetParameterAsText(13)

try:

	#     Variables defined:      
	#     ALPHA, BETA: distance friction coefficeints 
	#     H: population / employment ratio
	#     E: service employment / population ratio
	#     N: total number of tracts the city is divided into
	#     D(i,j): distance between tracts i and j
	#     A(i,j), B(i,j): matrices G, T in the Garin-Lowry model
	#     BEMP(i): basic employment vectors [known]
	#     POP(i), SEMP(i): population & service employment vectors
	#                      [variables to be solved]
	#     other variables: intermediates for computational purposes,
	#   

	# Get the total number of rows
	N = int(arcpy.GetCount_management(locationFL).getOutput(0))

	# Vector: origin id, destination id, basic employment
	BEMP = [0 for x in xrange(N)]
	OZONE = [0 for x in xrange(N)]
	DZONE = [0 for x in xrange(N)]

	# Read in origin id, destination id, and basic employment
	counter = 0
	with arcpy.da.SearchCursor(locationFL, (locationIdField, basicEmplField)) as cursor:
		for row in sorted(cursor):
			#print('TRTID: {0}, BEMP1: {1}'.format(row[0], row[1]))
			OZONE[counter] = int(row[0])
			DZONE[counter] = int(row[0])
			BEMP[counter] = float(row[1])
			counter += 1

	# Matrix: distance
	D = [[0 for x in xrange(N)] for x in xrange(N)]

	# Read in distance matrix
	cursor2 = arcpy.SearchCursor(distanceTable,
								 fields = distanceField + '; ' + originIdField + '; ' + destIdField,
								 sort_fields = originIdField + ' A; ' + destIdField + ' A')
	row = cursor2.next()
	for i in range(N):
		for j in range(N):
			if row:
				D[i][j] = float(row.getValue(distanceField))
				row = cursor2.next()
			else:
				break
	
	#     Step 1. Define parameters & Input data

	#     Input the values of ALPHA, BETA, H, E
	ALPHA = float(strALPHA)
	BETA = float(strBETA)
	H = float(strH)
	E = float(strE)

	#     Step 2. Build matrices A, B, I-A*B, based on D(i,j)

	#     Derive matrix Aij, Bij first
	#     DOMA(i) & DOMB(i) are the denominators in matrix formula.
	DOMA = [0 for x in xrange(N)]
	DOMB = [0 for x in xrange(N)]

	A = [[0 for x in xrange(N)] for x in xrange(N)]
	B = [[0 for x in xrange(N)] for x in xrange(N)]

	# Check which distance decay function is chosen
	if distanceDecayFunc == "Power":
		for i in range(N):
			for j in range(N):
				DOMA[i] = DOMA[i] + D[j][i]**(-BETA)
				DOMB[i] = DOMB[i] + D[j][i]**(-ALPHA)

		for i in range(N):
			for j in range(N):
				A[j][i] = H * D[j][i]**(-BETA) / DOMA[j]
				B[j][i] = E * D[j][i]**(-ALPHA) / DOMB[j]
	elif distanceDecayFunc == "Exponential":
		for i in range(N):
			for j in range(N):
				DOMA[i] = DOMA[i] + math.exp((-BETA) * D[j][i])
				DOMB[i] = DOMB[i] + math.exp((-ALPHA) * D[j][i])

		for i in range(N):
			for j in range(N):
				A[j][i] = H * math.exp((-BETA) * D[j][i]) / DOMA[j]
				B[j][i] = E * math.exp((-ALPHA) * D[j][i]) / DOMB[j]
	else:
		for i in range(N):
			for j in range(N):
				DOMA[i] = DOMA[i] + math.exp((-0.5) * D[j][i]**2 / BETA**2) / (math.sqrt(2*math.pi) * BETA)
				DOMB[i] = DOMB[i] + math.exp((-0.5) * D[j][i]**2 / ALPHA**2) / (math.sqrt(2*math.pi) * ALPHA)

		for i in range(N):
			for j in range(N):
				A[j][i] = H * (math.exp((-0.5) * D[j][i]**2 / BETA**2) / (math.sqrt(2*math.pi) * BETA)) / DOMA[j]
				B[j][i] = E * (math.exp((-0.5) * D[j][i]**2 / ALPHA**2) / (math.sqrt(2*math.pi) * ALPHA)) / DOMB[j]

	#     Derive the matrix I-A*B, represented by IAB here
	IAB = [[0 for x in xrange(N)] for x in xrange(N)]

	for i in range(N):
		for j in range(N):
			for m in range(N):
				IAB[j][i] = IAB[j][i] + A[m][i]*B[j][m]
			if i == j:
				IAB[j][i] = 1.0-IAB[j][i]
			else:
				IAB[j][i] = -IAB[j][i]

	#     Step 3. Prepare the data for solving the model.
	#     Since it is a given-employment problem, in the
	#       system of linear equations: AA*X=BB, AA is IAB,
	#       BB is A*BEMP, and X is POP.

	AA = [[0 for x in xrange(N)] for x in xrange(N)]
	BB = [0 for x in xrange(N)]

	for i in range(N):
		for j in range(N):
			AA[j][i] = IAB[j][i]
			BB[i] = BB[i] + A[j][i]*BEMP[j]

	#     Step 4. Solve the system of linear equation, AA*X=BB

	#     Factor AA matrix, print out INFO (indicating if the solution
	#       exists).

	IPVT = [0 for x in xrange(N)]
	err_info = 0

	ludcomp(AA, N, N, IPVT, err_info)
	#print('Error code: {0}'.format(err_info))

	#     Solve for x, which is vector POP
	lusolve(AA, BB, N, N, IPVT)

	POP = [0 for x in xrange(N)]
	SEMP = [0 for x in xrange(N)]

	for i in range(N):
		POP[i] = BB[i]

	#     Solve for the vetcor SEMP (=B*POP)
	for i in range(N):
		for j in range(N):
			SEMP[i] = SEMP[i] + B[j][i]*POP[j]

	#     Step 5. Write out POP and SEMP to feature class fields
	cursor3 = arcpy.UpdateCursor(locationFL,
								 fields = locationIdField + '; ' + popField + '; ' + serviceEmplField,
								 sort_fields = locationIdField + ' A')

	counter = 0
	for row in cursor3:
		row.setValue(popField, POP[counter])
		row.setValue(serviceEmplField, SEMP[counter])
		cursor3.updateRow(row)
		counter += 1

	# Delete cursor and row objects to remove locks on the data
	del row
	del cursor3

except Exception as e:
	print e.message
