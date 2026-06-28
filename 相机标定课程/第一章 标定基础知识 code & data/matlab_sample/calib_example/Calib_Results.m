% Intrinsic and Extrinsic Camera Parameters
%
% This script file can be directly executed under Matlab to recover the camera intrinsic and extrinsic parameters.
% IMPORTANT: This file contains neither the structure of the calibration objects nor the image coordinates of the calibration points.
%            All those complementary variables are saved in the complete matlab data file Calib_Results.mat.
% For more information regarding the calibration model visit http://www.vision.caltech.edu/bouguetj/calib_doc/


%-- Focal length:
fc = [ 657.446107869218281 ; 657.876660256090418 ];

%-- Principal point:
cc = [ 303.185319795283419 ; 242.708481163875661 ];

%-- Skew coefficient:
alpha_c = 0.000000000000000;

%-- Distortion coefficients:
kc = [ -0.255414841834118 ; 0.124449907410458 ; -0.000216975662453 ; 0.000074351611502 ; 0.000000000000000 ];

%-- Focal length uncertainty:
fc_error = [ 0.342478384326952 ; 0.370050216441834 ];

%-- Principal point uncertainty:
cc_error = [ 0.680897728174590 ; 0.613398692047898 ];

%-- Skew coefficient uncertainty:
alpha_c_error = 0.000000000000000;

%-- Distortion coefficients uncertainty:
kc_error = [ 0.002599662265258 ; 0.010262447934175 ; 0.000141999997628 ; 0.000139053529017 ; 0.000000000000000 ];

%-- Image size:
nx = 640;
ny = 480;


%-- Various other variables (may be ignored if you do not use the Matlab Calibration Toolbox):
%-- Those variables are used to control which intrinsic parameters should be optimized

n_ima = 20;						% Number of calibration images
est_fc = [ 1 ; 1 ];					% Estimation indicator of the two focal variables
est_aspect_ratio = 1;				% Estimation indicator of the aspect ratio fc(2)/fc(1)
center_optim = 1;					% Estimation indicator of the principal point
est_alpha = 0;						% Estimation indicator of the skew coefficient
est_dist = [ 1 ; 1 ; 1 ; 1 ; 0 ];	% Estimation indicator of the distortion coefficients


%-- Extrinsic parameters:
%-- The rotation (omc_kk) and the translation (Tc_kk) vectors for every calibration image and their uncertainties

%-- Image #1:
omc_1 = [ 1.654979e+00 ; 1.651950e+00 ; -6.693785e-01 ];
Tc_1  = [ -1.778374e+02 ; -8.398000e+01 ; 8.530169e+02 ];
omc_error_1 = [ 7.812500e-04 ; 1.011092e-03 ; 1.308289e-03 ];
Tc_error_1  = [ 8.841143e-01 ; 8.025597e-01 ; 4.556879e-01 ];

%-- Image #2:
omc_2 = [ 1.849156e+00 ; 1.900607e+00 ; -3.965517e-01 ];
Tc_2  = [ -1.551827e+02 ; -1.595655e+02 ; 7.575717e+02 ];
omc_error_2 = [ 8.172229e-04 ; 1.002937e-03 ; 1.578245e-03 ];
Tc_error_2  = [ 7.893804e-01 ; 7.112979e-01 ; 4.486902e-01 ];

%-- Image #3:
omc_3 = [ 1.742658e+00 ; 2.077703e+00 ; -5.047326e-01 ];
Tc_3  = [ -1.254237e+02 ; -1.748215e+02 ; 7.754674e+02 ];
omc_error_3 = [ 7.479819e-04 ; 1.062092e-03 ; 1.630074e-03 ];
Tc_error_3  = [ 8.069634e-01 ; 7.278935e-01 ; 4.317232e-01 ];

%-- Image #4:
omc_4 = [ 1.828122e+00 ; 2.116895e+00 ; -1.102805e+00 ];
Tc_4  = [ -6.462259e+01 ; -1.550615e+02 ; 7.790748e+02 ];
omc_error_4 = [ 6.766472e-04 ; 1.098727e-03 ; 1.532701e-03 ];
Tc_error_4  = [ 8.131572e-01 ; 7.265964e-01 ; 3.481221e-01 ];

%-- Image #5:
omc_5 = [ 1.079474e+00 ; 1.922456e+00 ; -2.527743e-01 ];
Tc_5  = [ -9.245227e+01 ; -2.292206e+02 ; 7.367000e+02 ];
omc_error_5 = [ 6.576986e-04 ; 1.036477e-03 ; 1.169465e-03 ];
Tc_error_5  = [ 7.744317e-01 ; 6.932382e-01 ; 4.239268e-01 ];

%-- Image #6:
omc_6 = [ -1.701426e+00 ; -1.929187e+00 ; -7.919921e-01 ];
Tc_6  = [ -1.490063e+02 ; -7.976434e+01 ; 4.447823e+02 ];
omc_error_6 = [ 6.341668e-04 ; 1.027705e-03 ; 1.409680e-03 ];
Tc_error_6  = [ 4.639109e-01 ; 4.284543e-01 ; 3.605897e-01 ];

%-- Image #7:
omc_7 = [ 1.996541e+00 ; 1.931351e+00 ; 1.311342e+00 ];
Tc_7  = [ -8.305704e+01 ; -7.785763e+01 ; 4.400375e+02 ];
omc_error_7 = [ 1.223015e-03 ; 6.298351e-04 ; 1.472920e-03 ];
Tc_error_7  = [ 4.658923e-01 ; 4.187191e-01 ; 3.824630e-01 ];

%-- Image #8:
omc_8 = [ 1.961109e+00 ; 1.824083e+00 ; 1.327096e+00 ];
Tc_8  = [ -1.702091e+02 ; -1.036771e+02 ; 4.618354e+02 ];
omc_error_8 = [ 1.166961e-03 ; 6.411884e-04 ; 1.412010e-03 ];
Tc_error_8  = [ 5.088243e-01 ; 4.547195e-01 ; 4.308058e-01 ];

%-- Image #9:
omc_9 = [ -1.363577e+00 ; -1.980545e+00 ; 3.208251e-01 ];
Tc_9  = [ -2.042706e+00 ; -2.252965e+02 ; 7.284682e+02 ];
omc_error_9 = [ 7.872848e-04 ; 1.019024e-03 ; 1.311479e-03 ];
Tc_error_9  = [ 7.640358e-01 ; 6.826135e-01 ; 4.379015e-01 ];

%-- Image #10:
omc_10 = [ -1.513038e+00 ; -2.086719e+00 ; 1.885227e-01 ];
Tc_10  = [ -2.976872e+01 ; -3.006248e+02 ; 8.600536e+02 ];
omc_error_10 = [ 9.578023e-04 ; 1.149596e-03 ; 1.737090e-03 ];
Tc_error_10  = [ 9.182623e-01 ; 8.114012e-01 ; 5.801185e-01 ];

%-- Image #11:
omc_11 = [ -1.793008e+00 ; -2.064944e+00 ; -4.802198e-01 ];
Tc_11  = [ -1.512175e+02 ; -2.355812e+02 ; 7.046386e+02 ];
omc_error_11 = [ 8.591073e-04 ; 1.086023e-03 ; 1.873805e-03 ];
Tc_error_11  = [ 7.528725e-01 ; 6.946891e-01 ; 5.695418e-01 ];

%-- Image #12:
omc_12 = [ -1.838880e+00 ; -2.087291e+00 ; -5.160742e-01 ];
Tc_12  = [ -1.336245e+02 ; -1.773935e+02 ; 6.048182e+02 ];
omc_error_12 = [ 7.326832e-04 ; 1.044782e-03 ; 1.734712e-03 ];
Tc_error_12  = [ 6.411379e-01 ; 5.875231e-01 ; 4.770619e-01 ];

%-- Image #13:
omc_13 = [ -1.918764e+00 ; -2.116523e+00 ; -5.947342e-01 ];
Tc_13  = [ -1.328176e+02 ; -1.437201e+02 ; 5.446762e+02 ];
omc_error_13 = [ 6.837124e-04 ; 1.033857e-03 ; 1.710131e-03 ];
Tc_error_13  = [ 5.756506e-01 ; 5.259837e-01 ; 4.339755e-01 ];

%-- Image #14:
omc_14 = [ -1.954177e+00 ; -2.124584e+00 ; -5.850837e-01 ];
Tc_14  = [ -1.237110e+02 ; -1.372844e+02 ; 4.907459e+02 ];
omc_error_14 = [ 6.436228e-04 ; 1.013397e-03 ; 1.676201e-03 ];
Tc_error_14  = [ 5.194258e-01 ; 4.734946e-01 ; 3.900538e-01 ];

%-- Image #15:
omc_15 = [ -2.110640e+00 ; -2.253791e+00 ; -4.957908e-01 ];
Tc_15  = [ -1.992531e+02 ; -1.346393e+02 ; 4.748480e+02 ];
omc_error_15 = [ 7.436932e-04 ; 9.485659e-04 ; 1.829370e-03 ];
Tc_error_15  = [ 5.090019e-01 ; 4.694797e-01 ; 4.202827e-01 ];

%-- Image #16:
omc_16 = [ 1.887022e+00 ; 2.336215e+00 ; -1.734242e-01 ];
Tc_16  = [ -1.609976e+01 ; -1.705035e+02 ; 6.955814e+02 ];
omc_error_16 = [ 1.019896e-03 ; 1.080104e-03 ; 2.263069e-03 ];
Tc_error_16  = [ 7.254114e-01 ; 6.479269e-01 ; 4.985035e-01 ];

%-- Image #17:
omc_17 = [ -1.612598e+00 ; -1.953339e+00 ; -3.478740e-01 ];
Tc_17  = [ -1.353432e+02 ; -1.390756e+02 ; 4.899986e+02 ];
omc_error_17 = [ 6.369539e-04 ; 9.820928e-04 ; 1.391258e-03 ];
Tc_error_17  = [ 5.128281e-01 ; 4.696560e-01 ; 3.472089e-01 ];

%-- Image #18:
omc_18 = [ -1.341444e+00 ; -1.692592e+00 ; -2.974499e-01 ];
Tc_18  = [ -1.854805e+02 ; -1.579201e+02 ; 4.410043e+02 ];
omc_error_18 = [ 7.324857e-04 ; 9.571257e-04 ; 1.102811e-03 ];
Tc_error_18  = [ 4.660469e-01 ; 4.278264e-01 ; 3.402203e-01 ];

%-- Image #19:
omc_19 = [ -1.925587e+00 ; -1.837812e+00 ; -1.440904e+00 ];
Tc_19  = [ -1.066426e+02 ; -7.967194e+01 ; 3.339780e+02 ];
omc_error_19 = [ 6.358231e-04 ; 1.108896e-03 ; 1.435600e-03 ];
Tc_error_19  = [ 3.613071e-01 ; 3.265433e-01 ; 3.187694e-01 ];

%-- Image #20:
omc_20 = [ NaN ; NaN ; NaN ];
Tc_20  = [ NaN ; NaN ; NaN ];
omc_error_20 = [ NaN ; NaN ; NaN ];
Tc_error_20  = [ NaN ; NaN ; NaN ];

