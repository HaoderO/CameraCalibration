if not exist build md build
cd build

cmake -G "Visual Studio 16 2019"^
	..

cd ..
pause