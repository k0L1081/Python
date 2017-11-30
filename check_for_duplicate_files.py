# Load Package(s)
import pandas as pd
import os
import hashlib
import filecmp
import sys

if __name__ == '__main__':
    if (len(sys.argv) < 3):
        print(''); print('Script terminated because of insufficient number of arguments.')
        print(''); print('Please execute script in the following format:')
        print('python <script_file> <working_directory> <output_file>')
        sys.exit()
    else:
        # Set working directory: Third argument in command line
        working_directory = sys.argv[1]
        os.chdir(working_directory)
        print(''); print('Working directory set to:', os.getcwd()); print('')

        # Set output file: Fourth argument in command line
        output_file = sys.argv[2]

    # Declare variable(s).
    i = 0
    group_ID = 0
    current_group_ID = 0
    size = 0
    match_exists = False

    # Create function(s).
    # Get file hash.
    def get_file_hash(path):
        return(hashlib.md5(open(path,'rb').read()).hexdigest())

    # Create data frame to hold file entries.
    df_files = pd.DataFrame(columns = ['name', 'path', 'size_bytes', 'group_ID', 'full_path'])

    # Recursively parse through all levels of specified working directory.
    for directory, directories, files in os.walk(working_directory, topdown = True, followlinks = True):
        for file in files:
            try:
                path = os.path.join(directory, file)
                os.stat(path)

            # Include exception handling (E.g., for broken links).
            except OSError as e:

                # If broken link exists, ignore.
                continue
            finally:
                #print(path)
                
                # Get file size.
                size = os.path.getsize(path)
                
                match_exists = False
                
                # Compare current file size to file sizes of files in list.
                for index, row in df_files.iterrows():

                    # If there is a file size match:
                    if (size == row['size_bytes']):
                        
                        # Compare file hash of current file to matched file.
                        # If there is a file hash match:
                        if (get_file_hash(path) == get_file_hash(row['full_path'])):
                            
                            # Compare file bytes of current file to matched file.
                            if (filecmp.cmp(path, row['full_path'], shallow=True)):
                                match_exists = True
                                break

                if(match_exists):
                    group_ID = row['group_ID']
                else:
                    current_group_ID = current_group_ID + 1
                    group_ID = current_group_ID

                df_files.loc[i, ['name', 'path', 'size_bytes', 'group_ID', 'full_path']] = [file, directory,
                                                                                            size, group_ID,
                                                                                            os.path.join(directory, file)]
            i = i + 1

    # Duplicate files will have the same group ID.
    # Compute list of duplicate group IDs.
    duplicate_group_IDs = df_files[df_files['group_ID'].duplicated()]['group_ID'].unique()

    # Filter out file information for duplicate group IDs.
    df_duplicate_files = df_files[df_files['group_ID'].isin(duplicate_group_IDs)][['name', 'full_path', 'group_ID']]
    df_duplicate_files = df_duplicate_files.reset_index(drop=True)

    #duplicate_files_csv_path = os.path.join(os.getcwd(), 'duplicate_files.csv')
    df_duplicate_files.to_csv(output_file)

    # Print out the duplicate files and their group IDs.
    print(df_duplicate_files)

    print(''); print('Data frame of duplicate files written to:', output_file)